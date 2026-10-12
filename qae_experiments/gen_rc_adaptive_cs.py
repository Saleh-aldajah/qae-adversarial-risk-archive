#!/usr/bin/env python3
"""gen_rc_adaptive_cs.py — derive time-uniform confidence-sequence intervals
for the v24 adaptive RC ladder (stopping: >=50 failures or 20,000 trials).
Reads repeated_cycle_adaptive*_v24.csv (raw counts unchanged), writes
data/rc_adaptive_cs_v24.csv with cs_lo/cs_hi from stats_intervals.cs_interval.
The runners' Wilson ci_lo/ci_hi columns are pointwise descriptive only;
inferential intervals for the adaptive ladder come from this file."""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats_intervals import cs_interval, cs_upper_zero

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SRC = [
    "repeated_cycle_adaptive_bb72_v24.csv",
    "repeated_cycle_adaptive_bb144_v24.csv",
    "repeated_cycle_adaptive_bb288_v24.csv",
    "repeated_cycle_adaptive_p010_bb72_v24.csv",
    "repeated_cycle_adaptive_p010_bb144_v24.csv",
    "repeated_cycle_adaptive_p010_bb288_v24.csv",
]
out_rows = []
for name in SRC:
    with open(os.path.join(DATA, name)) as fh:
        for r in csv.DictReader(fh):
            k, n = int(r["failures"]), int(r["trials"])
            lo, hi = cs_interval(k, n, alpha=0.05)
            out_rows.append({
                "code": r["code"], "p": r["p"], "rounds": r["rounds"],
                "trials": n, "failures": k, "lfr": r["lfr"],
                "cs_lo": f"{lo:.6g}", "cs_hi": f"{hi:.6g}",
                "method": "Robbins mixture CS (time-uniform), alpha=0.05",
                "stop_rule": ">=50 failures or 20000 trials (pinned)",
                "source_file": name,
            })
out = os.path.join(DATA, "rc_adaptive_cs_v24.csv")
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out_rows[0]))
    w.writeheader(); w.writerows(out_rows)
print(f"wrote {out}: {len(out_rows)} rows")
for r in out_rows:
    print(f"  {r['code']:6s} p={r['p']:5s} k={r['failures']:3d}/{r['trials']:6d} "
          f"CS95=[{r['cs_lo']},{r['cs_hi']}]")
