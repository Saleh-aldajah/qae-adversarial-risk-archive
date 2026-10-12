"""
compute_lambda.py  —  Distance-ladder suppression factor Lambda (v22).

Reads the adaptive repeated-cycle CSVs and writes data/lambda_ladder.csv:
LFR ratios between successive codes on the d=6/12/18 ladder, with
log-method 95% CIs, and Lambda per Delta d = 2 step (ratio^(2/Delta d)).
Deterministic; no randomness. Runtime < 1 s.

Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
import csv, math
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def load():
    data = {}
    for c in ["bb72", "bb144", "bb288"]:
        for r in csv.DictReader(open(ROOT / "data" / f"repeated_cycle_adaptive_{c}.csv")):
            data[(c.upper(), float(r["p"]))] = (int(r["failures"]), int(r["trials"]))
        r = list(csv.DictReader(open(ROOT / "data" / f"repeated_cycle_adaptive_p010_{c}.csv")))[0]
        data[(c.upper(), 0.010)] = (int(r["failures"]), int(r["trials"]))
    return data

def rr_lam(ka, na, kb, nb, steps):
    rr = (ka / na) / (kb / nb)
    se = math.sqrt(1 / ka - 1 / na + 1 / kb - 1 / nb)
    lo, hi = math.exp(math.log(rr) - 1.959964 * se), math.exp(math.log(rr) + 1.959964 * se)
    return rr, lo, hi, rr ** (1 / steps), lo ** (1 / steps), hi ** (1 / steps)

data = load()
rows = []
for p, hi_key, lo_key, steps in [
        (0.008, ("BB72", 0.008), ("BB144", 0.008), 3),
        (0.010, ("BB72", 0.010), ("BB144", 0.010), 3),
        (0.010, ("BB144", 0.010), ("BB288", 0.010), 3),
        (0.012, ("BB72", 0.012), ("BB144", 0.012), 3),
        (0.012, ("BB144", 0.012), ("BB288", 0.012), 3),
        (0.010, ("BB72", 0.010), ("BB288", 0.010), 6),
        (0.012, ("BB72", 0.012), ("BB288", 0.012), 6)]:
    (ka, na), (kb, nb) = data[hi_key], data[lo_key]
    rr, lo, hi, lam, llo, lhi = rr_lam(ka, na, kb, nb, steps)
    rows.append({"p": p, "step": f"{hi_key[0]}->{lo_key[0]}",
                 "fails_hi": ka, "trials_hi": na, "fails_lo": kb, "trials_lo": nb,
                 "lfr_ratio": round(rr, 3), "ratio_ci_lo": round(lo, 3), "ratio_ci_hi": round(hi, 3),
                 "lambda_per_2": round(lam, 4), "lambda_ci_lo": round(llo, 4), "lambda_ci_hi": round(lhi, 4)})
out = ROOT / "data" / "lambda_ladder.csv"
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print(f"wrote {out.name}: {len(rows)} rows")
