"""
compute_lambda_v24.py  —  Distance-ladder suppression factor Lambda (v24).

Reads the v24 prior-aligned adaptive repeated-cycle CSVs
(data/repeated_cycle_adaptive_{bb72,bb144,bb288}_v24.csv and, when present,
data/repeated_cycle_adaptive_p010_{code}_v24.csv) and writes
data/lambda_ladder_v24.csv.

v25 policy (review Sec. 4.3): every arm of the ladder is adaptively
stopped (>=50 failures or 20,000 trials, pinned), so fixed-N formulas do
NOT apply. All endpoints come from stats_intervals confidence sequences
(Robbins uniform-mixture CS, time-uniform, valid at the stopping time):
  * both counts > 0: two-sided ratio CI
    [CSlo(ka, a/4)/CShi(kb, a/4), CShi(ka, a/4)/CSlo(kb, a/4)],
    joint >= 1-a over the four endpoints (Bonferroni), a = 0.05;
  * denominator count = 0: one-sided ratio lower bound
    CSlo(ka, a/2) / CShi(0, nb, a/2), joint >= 1-a (two endpoints);
  * numerator count = 0: ratio upper bound (not our regime; omitted).
Lambda = ratio^(1/steps) per Delta d = 2 step; reported as point estimate
from the observed ratio with the CS-based interval, or ">Lambda_lo" when
the denominator arm has zero failures.

Deterministic; no randomness. Runtime < 1 s.
"""
import csv, math, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from stats_intervals import cs_interval

A = 0.05


def cs_pair(k, n, alpha):
    """(lower, upper) CS endpoints at level 1-alpha each."""
    return cs_interval(k, n, alpha)


def load():
    data = {}
    for c in ["bb72", "bb144", "bb288"]:
        for r in csv.DictReader(open(ROOT / "data" / f"repeated_cycle_adaptive_{c}_v24.csv")):
            data[(c.upper(), float(r["p"]))] = (int(r["failures"]), int(r["trials"]))
        f = ROOT / "data" / f"repeated_cycle_adaptive_p010_{c}_v24.csv"
        if f.exists():
            r = list(csv.DictReader(open(f)))[0]
            data[(c.upper(), 0.010)] = (int(r["failures"]), int(r["trials"]))
    return data


def rr_lam(ka, na, kb, nb, steps):
    """Returns (kind, rr_or_lo, lo, hi, lam_or_lamlo, lam_lo, lam_hi).
    All endpoints are CS-based (sequential stopping); see header."""
    if kb > 0 and ka > 0:
        rr = (ka / na) / (kb / nb)
        lo_a, hi_a = cs_pair(ka, na, A / 4)
        lo_b, hi_b = cs_pair(kb, nb, A / 4)
        lo, hi = lo_a / hi_b, hi_a / lo_b if lo_b > 0 else float("inf")
        return ("two-sided-CS", rr, lo, hi, rr ** (1 / steps),
                lo ** (1 / steps), hi ** (1 / steps))
    if kb == 0 and ka > 0:
        lo_a, _ = cs_pair(ka, na, A / 2)
        _, hi_b = cs_pair(0, nb, A / 2)
        rr_lo = lo_a / hi_b
        return ("one-sided-CS", rr_lo, rr_lo, float("inf"), rr_lo ** (1 / steps),
                rr_lo ** (1 / steps), float("inf"))
    nan = float("nan")
    return ("undefined", nan, nan, nan, nan, nan, nan)


data = load()
rows = []
grid = []
for p in (0.004, 0.006, 0.008, 0.010, 0.012):
    if ("BB72", p) in data and ("BB144", p) in data:
        grid.append((p, ("BB72", p), ("BB144", p), 3))
    if ("BB144", p) in data and ("BB288", p) in data:
        grid.append((p, ("BB144", p), ("BB288", p), 3))
    if ("BB72", p) in data and ("BB288", p) in data:
        grid.append((p, ("BB72", p), ("BB288", p), 6))

for p, hi_key, lo_key, steps in grid:
    (ka, na), (kb, nb) = data[hi_key], data[lo_key]
    kind, rr, lo, hi, lam, llo, lhi = rr_lam(ka, na, kb, nb, steps)
    rows.append({"p": p, "step": f"{hi_key[0]}->{lo_key[0]}", "kind": kind,
                 "fails_hi": ka, "trials_hi": na, "fails_lo": kb, "trials_lo": nb,
                 "lfr_ratio": round(rr, 3) if rr == rr else "",
                 "ratio_ci_lo": round(lo, 3) if lo == lo else "",
                 "ratio_ci_hi": round(hi, 3) if hi == hi and hi != float("inf") else "",
                 "lambda_per_2": round(lam, 4) if lam == lam else "",
                 "lambda_ci_lo": round(llo, 4) if llo == llo else "",
                 "lambda_ci_hi": round(lhi, 4) if lhi == lhi and lhi != float("inf") else ""})

out = ROOT / "data" / "lambda_ladder_v24.csv"
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print(f"wrote {out.name}: {len(rows)} rows")
for r in rows:
    print(r)
