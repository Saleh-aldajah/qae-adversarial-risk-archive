#!/usr/bin/env python
"""ca02_analyze.py -- retrieve + decode the causal-ablation campaign and
evaluate the pre-registered tests (D1/D2/P1/P2/T1) against the pinned
predictions document.

Usage:  python ca02_analyze.py
Reads:  results/causal_jobs.json (+ the pinned predictions it references)
Writes: results/causal_results.csv, results/causal_verdict.json,
        results/counts_c_*.json
"""
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from ca_common import (DOSES_NS, PRED, RES, TIGHTEN_SHOTS, pick_tightening_cell,
                       ARCHIVE_CONSOL_CSV)
from ct_common import dump_json, sha256_file, wilson95
from tt_common import ROUNDS, build_dem, counts_to_observables
from ct01_pin_build_submit import get_service

COUNTS = RES
D = 5  # REP5 throughout


def decode_counts(counts, d=D):
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


def z_one_sided(f1, n1, f2, n2):
    """one-sided two-proportion z for p1 > p2."""
    p1, p2 = f1 / n1, f2 / n2
    pp = (f1 + f2) / (n1 + n2)
    se = math.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se if se > 0 else 0.0
    from math import erfc
    pval = 0.5 * erfc(z / math.sqrt(2))
    return z, pval


def spearman(x, y):
    """Spearman rho on pre-ranked inputs (ties averaged)."""
    n = len(x)
    xm, ym = sum(x) / n, sum(y) / n
    cov = sum((a - xm) * (b - ym) for a, b in zip(x, y))
    vx = sum((a - xm) ** 2 for a in x)
    vy = sum((b - ym) ** 2 for b in y)
    return cov / math.sqrt(vx * vy) if vx > 0 and vy > 0 else 0.0


def ranks(vals):
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    r = [0.0] * len(vals)
    i = 0
    while i < len(vals):
        j = i
        while j + 1 < len(vals) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2.0
        i = j + 1
    return r


def main():
    payload = json.loads((RES / "causal_jobs.json").read_text())
    pred_path = PRED / payload["predictions_file"]
    assert sha256_file(pred_path) == payload["predictions_sha256"], \
        "pinned predictions digest mismatch"
    preds = json.loads(pred_path.read_text())
    meta = json.loads(
        (HERE / "circuits" / "circuits_metadata_causal.json").read_text())

    job_of_group = {}
    for j in payload["jobs"]:
        job_of_group.setdefault(j["group"], j["job_id"])

    service = get_service()
    rows = []
    for gname, jid in sorted(job_of_group.items()):
        job = service.job(jid)
        status = job.status()
        print(f"[{gname}] job {jid} status={status}")
        if "DONE" not in str(status):
            print("  ... not done; skipping")
            continue
        res = job.result()
        circs = [c for c in meta["circuits"] if c["arm"] == gname.split("_")[1]]
        assert len(res) == len(circs), (len(res), len(circs))
        for c, pr in zip(circs, res):
            counts = pr.data["meas"].get_counts()
            shots, fails = decode_counts(counts)
            lo, hi = wilson95(fails, shots)
            rows.append({**{k: c.get(k) for k in
                            ("arm", "code", "basis", "name", "dose_ns",
                             "rank", "p", "variant")},
                         "shots": shots, "failures": fails,
                         "ler": fails / shots, "ci_lo": lo, "ci_hi": hi,
                         "job_id": jid})
            dump_json(COUNTS / f"counts_c_{c['arm'].lower()}_"
                               f"{c['code'].lower()}_{c['basis'].lower()}_"
                               f"{c['name']}.json",
                      {"job_id": jid, "counts": counts,
                       "retrieved_utc":
                           datetime.now(timezone.utc).isoformat()})
    if not rows:
        print("[decode] no completed jobs yet")
        return

    with open(RES / "causal_results.csv", "w", newline="") as f:
        wcsv = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wcsv.writeheader()
        wcsv.writerows(rows)
    print(f"[decode] {len(rows)} rows -> causal_results.csv")

    # ---------- pre-registered tests ----------
    verdict = {"evaluated_utc": datetime.now(timezone.utc).isoformat(),
               "predictions_file": payload["predictions_file"],
               "predictions_sha256": payload["predictions_sha256"],
               "tests": []}

    by = {r["name"]: r for r in rows}
    d_rows = [r for r in rows if r["arm"] == "D"]
    p_rows = [r for r in rows if r["arm"] == "P"]
    t_rows = [r for r in rows if r["arm"] == "T"]

    if len(d_rows) == len(DOSES_NS):
        d0 = by[f"dose{DOSES_NS[0]:g}ns"]
        d4 = by[f"dose{DOSES_NS[-1]:g}ns"]
        z, pval = z_one_sided(d4["failures"], d4["shots"],
                              d0["failures"], d0["shots"])
        verdict["tests"].append({
            "id": "D1", "z": z, "p_one_sided": pval, "alpha": 0.01,
            "lfr_dose0": d0["ler"], "lfr_dose_max": d4["ler"],
            "pass": pval < 0.01 and d4["ler"] > d0["ler"]})
        lrs = [by[f"dose{x:g}ns"]["ler"] for x in DOSES_NS]
        verdict["tests"].append({
            "id": "D2", "lfr_by_dose": lrs,
            "monotone_nondec": all(b >= a for a, b in zip(lrs, lrs[1:]))})

    if len(p_rows) == 8:
        # metrology rank was assigned best->0; measured LFR rank best->0
        met_rank = [float(r["rank"]) for r in p_rows]
        lfr_rank = ranks([r["ler"] for r in p_rows])
        rho = spearman(met_rank, lfr_rank)
        best4 = [r for r in p_rows if r["rank"] < 4]
        worst4 = [r for r in p_rows if r["rank"] >= 4]
        fb, nb = sum(r["failures"] for r in best4), sum(r["shots"] for r in best4)
        fw, nw = sum(r["failures"] for r in worst4), sum(r["shots"] for r in worst4)
        z2, pval2 = z_one_sided(fw, nw, fb, nb)
        verdict["tests"].append({
            "id": "P1", "spearman_rho": rho, "threshold": 0.75,
            "pass": rho >= 0.75})
        verdict["tests"].append({
            "id": "P2", "z": z2, "p_one_sided": pval2, "alpha": 0.01,
            "best4_lfr": fb / nb, "worst4_lfr": fw / nw,
            "pass": pval2 < 0.01 and fw / nw > fb / nb})

    if t_rows:
        cell = pick_tightening_cell(ARCHIVE_CONSOL_CSV)
        f_new = sum(r["failures"] for r in t_rows)
        n_new = sum(r["shots"] for r in t_rows)
        f_m, n_m = cell["failures"] + f_new, cell["shots"] + n_new
        lo_m, hi_m = wilson95(f_m, n_m)
        w_old = cell["ci_hi"] - cell["ci_lo"]
        w_new = hi_m - lo_m
        verdict["tests"].append({
            "id": "T1", "cell": {k: cell[k] for k in
                                 ("code", "basis", "p")},
            "archived": {"failures": cell["failures"], "shots": cell["shots"],
                         "width": w_old},
            "new_campaign": {"failures": f_new, "shots": n_new},
            "merged": {"failures": f_m, "shots": n_m, "ci_lo": lo_m,
                       "ci_hi": hi_m, "width": w_new},
            "width_ratio": w_new / w_old if w_old else None,
            "pass": w_new < w_old})

    npass = sum(1 for t in verdict["tests"] if t.get("pass"))
    verdict["summary"] = (f"{npass}/{len(verdict['tests'])} "
                          "pre-registered tests passed")
    dump_json(RES / "causal_verdict.json", verdict)
    print(f"[verdict] {verdict['summary']} -> causal_verdict.json")


if __name__ == "__main__":
    main()
