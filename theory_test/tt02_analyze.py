#!/usr/bin/env python
"""tt02_analyze.py — retrieve theory-test jobs, decode, score against the
pre-registered predictions (results/theorytest_jobs.json carries the pinned
predictions sha256). Writes results/theorytest_results.csv +
verdict JSON. Token read from the readable handoff copy; never printed.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "ibm_demo"))
import ibm_demo_common as _idc
_idc.TOKEN_PATH = Path("/mnt/agents/temp/ibm_token.json")
import tt_common as _ttc
_ttc.TOKEN_PATH = _idc.TOKEN_PATH
from tt_common import (BACKEND_NAME, COUNTS, D_OF, RES, ROUNDS, T_OF,  # noqa: E402
                       arm_list, binom_tail, build_dem,
                       counts_to_observables, dump_json, wilson95)


def get_service():
    from qiskit_ibm_runtime import QiskitRuntimeService
    token = json.loads(_idc.TOKEN_PATH.read_text())["token"]
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
    jobs_payload = json.loads((RES / "theorytest_jobs.json").read_text())
    pred_sha = jobs_payload["predictions_sha256"]
    jobs = jobs_payload["jobs"]
    # group -> ordered arm list must mirror tt01_submit exactly
    arms = arm_list()
    groups = {}
    for a in arms:
        groups.setdefault((a["kind"], a["basis"]), []).append(a)
    job_of_group = {}
    for j in jobs:
        job_of_group.setdefault(j["group"], j["job_id"])

    service = get_service()
    rows = []
    for (kind, basis), group_arms in sorted(groups.items()):
        gname = f"{kind}_{basis.lower()}"
        jid = job_of_group[gname]
        job = service.job(jid)
        status = job.status()
        print(f"[{gname}] job {jid} status={status}")
        if str(status) not in ("DONE", "JobStatus.DONE"):
            print(f"  ... skipping (not done)"); continue
        res = job.result()
        assert len(res) == len(group_arms), (len(res), len(group_arms))
        for a, pr in zip(group_arms, res):
            counts = pr.data["meas"].get_counts()
            d = D_OF[a["code"]]
            shots, fails = decode_counts(counts, d)
            lo, hi = wilson95(fails, shots)
            rows.append({"code": a["code"], "basis": a["basis"],
                         "name": a["name"], "kind": kind, "shots": shots,
                         "failures": fails, "ler": fails / shots,
                         "ci_lo": lo, "ci_hi": hi, "job_id": jid,
                         **({"p": a["p"], "variant": a["variant"],
                             "inj_weight": len(a["mask"])} if kind == "stoch" else {})})
            dump_json(COUNTS / f"counts_{a['code'].lower()}_{basis.lower()}_{a['name']}_tt.json",
                      {"job_id": jid, "counts": counts,
                       "retrieved_utc": datetime.now(timezone.utc).isoformat()})
    # persist raw rows
    import csv
    if rows:
        keys = sorted({k for r in rows for k in r})
        with open(RES / "theorytest_results.csv", "w", newline="") as f:
            wcsv = csv.DictWriter(f, fieldnames=keys)
            wcsv.writeheader()
            for r in rows:
                wcsv.writerow(r)
    print(f"[decode] {len(rows)} arms decoded")

    # ---- score against pre-registered predictions ----
    preds_files = sorted((HERE / "predictions").glob("predictions_*.json"))
    preds = None
    from tt_common import sha256_file
    for pf in reversed(preds_files):
        if sha256_file(pf) == pred_sha:
            preds = json.loads(pf.read_text()); break
    assert preds is not None, "pinned predictions file not found / digest mismatch"
    proto = preds["protocol"]
    TOL_DET, TOL_STOCH = proto["TOL_DET"], proto["TOL_STOCH"]

    det = {(r["code"], r["basis"], r["name"]): r for r in rows if r["kind"] == "det"}
    verdicts = []
    for test in proto["tests"]:
        code, basis, arm, typ = test["code"], test["basis"], test["arm"], test["type"]
        if typ in ("bound", "sharp"):
            r = det.get((code, basis, arm))
            b = det.get((code, basis, "base"))
            if r is None or b is None:
                verdicts.append({**test, "verdict": "PENDING"}); continue
            if typ == "bound":
                ok = r["ler"] <= b["ler"] + TOL_DET
                verdicts.append({**test, "ler_base": b["ler"], "ler_arm": r["ler"],
                                 "margin": b["ler"] + TOL_DET - r["ler"],
                                 "verdict": "BOUND HOLDS" if ok else "BOUND VIOLATED"})
            else:
                ok = r["ler"] >= proto["SHARP_MIN"][code]
                verdicts.append({**test, "ler_arm": r["ler"],
                                 "verdict": "SHARP" if ok else "NOT SHARP"})
        else:  # stochastic
            p = float(test["arm"][1:]); d, t = D_OF[code], T_OF[code]
            pool = [r for r in rows if r["kind"] == "stoch" and r["code"] == code
                    and r["basis"] == basis and abs(r.get("p", -1) - p) < 1e-9]
            b = det.get((code, basis, "base"))
            if not pool or b is None:
                verdicts.append({**test, "verdict": "PENDING"}); continue
            shots = sum(r["shots"] for r in pool); fails = sum(r["failures"] for r in pool)
            ler = fails / shots; lo, hi = wilson95(fails, shots)
            d0_hi = b["ci_hi"]
            bound = d0_hi + binom_tail(d, t, p) + TOL_STOCH
            ok = ler <= bound
            verdicts.append({**test, "shots": shots, "failures": fails,
                             "ler": ler, "ci": [lo, hi], "d0_hi": d0_hi,
                             "bound_value": bound,
                             "verdict": "BOUND HOLDS" if ok else "BOUND VIOLATED"})
    out = {"analyzed_utc": datetime.now(timezone.utc).isoformat(),
           "predictions_sha256": pred_sha, "backend": BACKEND_NAME,
           "verdicts": verdicts}
    dump_json(RES / "theorytest_verdict.json", out)
    n_pass = sum(1 for v in verdicts if v["verdict"] in ("BOUND HOLDS", "SHARP"))
    n_fail = sum(1 for v in verdicts if v["verdict"] in ("BOUND VIOLATED", "NOT SHARP"))
    n_pend = sum(1 for v in verdicts if v["verdict"] == "PENDING")
    print(f"[verdict] pass={n_pass} fail={n_fail} pending={n_pend}")
    for v in verdicts:
        print("  ", v["code"], v["basis"], v["arm"], "->", v["verdict"],
              f"(ler={v.get('ler_arm', v.get('ler'))})" if v["verdict"] != "PENDING" else "")


if __name__ == "__main__":
    main()
