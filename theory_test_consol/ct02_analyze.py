#!/usr/bin/env python
"""ct02_analyze.py — retrieve consolidation jobs, decode (MWPM-DEM), and
score against the SHA-256-pinned pre-registration. Also runs the
cross-cycle replication comparison vs the 2026-08-28 campaign
(theory_test/results/theorytest_results.csv) and writes
results/consol_results.csv + consol_verdict.json + REPORT_CONSOL.md.
"""
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ct_common import (COUNTS, D_OF, PRED, RES, ROUNDS, T_OF, arm_list,
                       binom_tail, build_dem, counts_to_observables,
                       dump_json, poisson_tail, sha256_file, wilson95)
import ibm_demo_common as _idc
from pathlib import Path as _P
_idc.TOKEN_PATH = _P("/mnt/agents/temp/ibm_token.json")
TOKEN_PATH = _idc.TOKEN_PATH

CAMP1 = HERE.parent / "theory_test" / "results" / "theorytest_results.csv"


def get_service():
    from qiskit_ibm_runtime import QiskitRuntimeService
    token = json.loads(TOKEN_PATH.read_text())["token"]
    return QiskitRuntimeService(channel="ibm_quantum_platform", token=token)


def decode_counts(counts, d):
    from pymatching import Matching
    H, w, faults = build_dem(d, ROUNDS)
    m = Matching.from_check_matrix(H, weights=w, faults_matrix=faults)
    syndromes, logicals, mult = counts_to_observables(counts, d, ROUNDS)
    shots = failures = 0
    for syn, log, n in zip(syndromes, logicals, mult):
        pred = int(m.decode(syn)[0])
        shots += n
        failures += n * ((log ^ pred) != 0)
    return shots, failures


def main():
    payload = json.loads((RES / "consol_jobs.json").read_text())
    pred_sha = payload["predictions_sha256"]
    pred_path = PRED / payload["predictions_file"]
    assert sha256_file(pred_path) == pred_sha, "pinned predictions digest mismatch"
    preds = json.loads(pred_path.read_text())
    proto = preds["protocol"]
    TOL_DET, TOL_STOCH = proto["TOL_DET"], proto["TOL_STOCH"]
    lams = preds["lambda_N"]

    arms = arm_list(("A", "B"))
    groups = {}
    for a in arms:
        groups.setdefault((a["campaign"], a["kind"], a["basis"]),
                          []).append(a)
    job_of_group = {}
    for j in payload["jobs"]:
        job_of_group.setdefault(j["group"], j["job_id"])

    service = get_service()
    rows = []
    for (camp, kind, basis), group_arms in sorted(groups.items()):
        gname = f"{camp}_{kind}_{basis.lower()}"
        jid = job_of_group[gname]
        job = service.job(jid)
        status = job.status()
        print(f"[{gname}] job {jid} status={status}")
        if "DONE" not in str(status):
            print("  ... not done; skipping")
            continue
        res = job.result()
        assert len(res) == len(group_arms), (len(res), len(group_arms))
        for a, pr in zip(group_arms, res):
            counts = pr.data["meas"].get_counts()
            d = D_OF[a["code"]]
            shots, fails = decode_counts(counts, d)
            lo, hi = wilson95(fails, shots)
            rows.append({"campaign": camp, "code": a["code"],
                         "basis": basis, "name": a["name"], "kind": kind,
                         "shots": shots, "failures": fails,
                         "ler": fails / shots, "ci_lo": lo, "ci_hi": hi,
                         "job_id": jid,
                         **({"p": a["p"], "variant": a["variant"],
                             "inj_weight": len(a["mask"])}
                            if kind == "stoch" else {})})
            dump_json(COUNTS / f"counts_{camp.lower()}_{a['code'].lower()}"
                               f"_{basis.lower()}_{a['name']}_ct.json",
                      {"job_id": jid, "counts": counts,
                       "retrieved_utc": datetime.now(timezone.utc).isoformat()})
    if not rows:
        print("[decode] no completed jobs yet")
        return
    keys = sorted({k for r in rows for k in r})
    with open(RES / "consol_results.csv", "w", newline="") as f:
        wcsv = csv.DictWriter(f, fieldnames=keys)
        wcsv.writeheader()
        wcsv.writerows(rows)
    print(f"[decode] {len(rows)} arms decoded")

    det = {(r["campaign"], r["code"], r["basis"], r["name"]): r
           for r in rows if r["kind"] == "det"}
    verdicts = []
    for test in proto["tests"]:
        dev, code, basis, arm, typ = (test["device"], test["code"],
                                      test["basis"], test["arm"],
                                      test["type"])
        if typ in ("bound", "sharp"):
            r = det.get((dev, code, basis, arm))
            b = det.get((dev, code, basis, "base"))
            if r is None or b is None:
                verdicts.append({**test, "verdict": "PENDING"}); continue
            if typ == "bound":
                ok = r["ler"] <= b["ler"] + TOL_DET
                verdicts.append({**test, "ler_base": b["ler"],
                                 "ler_arm": r["ler"],
                                 "margin": b["ler"] + TOL_DET - r["ler"],
                                 "verdict": "BOUND HOLDS" if ok
                                 else "BOUND VIOLATED"})
            else:
                ok = r["ler"] >= proto["SHARP_MIN"][code]
                verdicts.append({**test, "ler_arm": r["ler"],
                                 "verdict": "SHARP" if ok else "NOT SHARP"})
        else:  # stochastic, campaign A only
            p = float(test["arm"][1:])
            d, t = D_OF[code], T_OF[code]
            pool = [r for r in rows if r["kind"] == "stoch"
                    and r["campaign"] == dev and r["code"] == code
                    and r["basis"] == basis
                    and abs(r.get("p", -1) - p) < 1e-9]
            b = det.get((dev, code, basis, "base"))
            if not pool or b is None:
                verdicts.append({**test, "verdict": "PENDING"}); continue
            shots = sum(r["shots"] for r in pool)
            fails = sum(r["failures"] for r in pool)
            ler = fails / shots
            lo, hi = wilson95(fails, shots)
            d0_hi = b["ci_hi"]
            naive = d0_hi + binom_tail(d, t, p) + TOL_STOCH
            lam = lams[dev][code]
            # Pr[Bin(d,p) + Pois(lam) >= t+1]
            comp_tail = 0.0
            for k in range(d + 1):
                pb = math.comb(d, k) * p ** k * (1 - p) ** (d - k)
                comp_tail += pb * poisson_tail(lam, t + 1 - k)
            composed = d0_hi + comp_tail + TOL_STOCH
            verdicts.append({**test, "shots": shots, "failures": fails,
                             "ler": ler, "ci": [lo, hi], "d0_hi": d0_hi,
                             "naive_bound": naive,
                             "composed_bound": composed,
                             "lambda_N": lam,
                             "verdict": ("BOTH HOLD" if ler <= naive
                                         else "NAIVE FALSIFIED, COMPOSED HOLDS"
                                         if ler <= composed
                                         else "COMPOSED VIOLATED")})
    # ---- cross-cycle replication vs campaign 1 (device A overlaps) ----
    repl = []
    if CAMP1.exists():
        with open(CAMP1) as f:
            c1 = [r for r in csv.DictReader(f) if r["kind"] == "det"]
        c1map = {(r["code"], r["basis"], r["name"]): r for r in c1}
        z = 2.807  # Bonferroni two-sided 0.05 over 12 overlapping arms
        for (code, basis, name), r1 in sorted(c1map.items()):
            r2 = det.get(("A", code, basis, name))
            if r2 is None:
                continue
            n1, k1 = int(r1["shots"]), int(r1["failures"])
            n2, k2 = r2["shots"], r2["failures"]
            p1, p2 = k1 / n1, k2 / n2
            se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
            dz = abs(p1 - p2) / se if se > 0 else 0.0
            repl.append({"code": code, "basis": basis, "arm": name,
                         "ler_20260828": p1, "ler_20260906": p2,
                         "abs_diff": abs(p1 - p2), "z": dz,
                         "consistent": bool(dz <= z)})
    out = {"analyzed_utc": datetime.now(timezone.utc).isoformat(),
           "predictions_sha256": pred_sha,
           "devices": preds["devices"], "layouts": preds["layouts"],
           "lambda_N": lams, "verdicts": verdicts,
           "replication_vs_20260828": repl}
    dump_json(RES / "consol_verdict.json", out)
    n_pass = sum(1 for v in verdicts
                 if v["verdict"] in ("BOUND HOLDS", "SHARP",
                                     "BOTH HOLD",
                                     "NAIVE FALSIFIED, COMPOSED HOLDS"))
    n_bad = sum(1 for v in verdicts
                if v["verdict"] in ("BOUND VIOLATED", "NOT SHARP",
                                    "COMPOSED VIOLATED"))
    n_pend = sum(1 for v in verdicts if v["verdict"] == "PENDING")
    n_cons = sum(1 for r in repl if r["consistent"])
    print(f"[verdict] pass={n_pass} fail={n_bad} pending={n_pend}; "
          f"replication consistent {n_cons}/{len(repl)}")
    for v in verdicts:
        print("  ", v["device"], v["code"], v["basis"], v["arm"], "->",
              v["verdict"])


if __name__ == "__main__":
    main()
