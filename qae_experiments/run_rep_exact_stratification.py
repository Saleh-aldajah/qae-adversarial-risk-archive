#!/usr/bin/env python3
"""
run_rep_exact_stratification.py — exact small-code stratification for the
repetition-code injection arms (review Sec. 11.2; supersedes random
mask-frequency sampling for REP3/REP5/REP7).

For distance d in {3, 5, 7} the single-round bit-flip adversary space has
2^d masks (8 / 32 / 128).  We MEASURE EVERY MASK exactly:

  * analytic: minimum-weight (= majority-vote) decoder response
              f(x) = 1[|x| > floor(d/2)], exact by enumeration;
  * circuit : noiseless Stim tableau simulation of the pinned extraction
              circuit (repetition parity checks, one round), majority vote on
              the final data readout — an independent implementation check.

The Bernoulli(p) injection expectation is then EXACT:
      LFR(p) = sum_x p^|x| (1-p)^(d-|x|) f(x),
with zero mask-sampling variance.  Because the per-mask responses are
deterministic and noiseless, reweighting them under other injection
distributions (e.g. a mask mixture pinned by hardware budget) carries no
additional statistical uncertainty; any such reuse is exact conditioning,
not a new estimate.

Outputs:
  data/rep_exact_masks_v24.csv   (per-mask responses, 168 rows)
  data/rep_exact_lfr_v24.csv     (exact LFR(p) curves on a p grid)
"""
import sys, csv
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "data"; OUT.mkdir(exist_ok=True)

from qae_utils import stable_seed  # noqa: E402  (recorded for provenance)

P_GRID = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30]
DS = [3, 5, 7]


def circuit_response(d, mask):
    """Noiseless tableau run of the one-round repetition extraction with the
    mask applied as X flips after preparation; majority vote on final data."""
    import stim
    c = stim.Circuit()
    c.append('R', list(range(d)))
    for q in range(d):
        if (mask >> q) & 1:
            c.append('X', q)
    # one extraction round: Z-checks (parity between neighbours), ancillas d+i
    for i in range(d - 1):
        c.append('R', d + i)
    for i in range(d - 1):
        c.append('CX', [i, d + i])
        c.append('CX', [i + 1, d + i])
    for i in range(d - 1):
        c.append('M', d + i)
    for q in range(d):
        c.append('M', q)
    sim = stim.TableauSimulator()
    sim.do(c)
    rec = None
    rec = getattr(sim, 'measurement_record', None)
    if rec is None:
        rec = sim.current_measurement_record()
    bits = [int(b) for b in rec][-(d):]
    return int(sum(bits) > d // 2)   # majority vote on |0>^d preparation


rows_m, rows_l = [], []
for d in DS:
    t = d // 2
    disagree = 0
    for mask in range(2 ** d):
        w = bin(mask).count('1')
        f_ana = int(w > t)
        f_sim = circuit_response(d, mask)
        disagree += int(f_ana != f_sim)
        rows_m.append(dict(exp='rep_exact_masks_v24', code=f'REP{d}', d=d,
                           mask=mask, weight=w,
                           response_analytic=f_ana, response_circuit=f_sim,
                           agree=int(f_ana == f_sim),
                           seed=stable_seed('REP-EXACT', d)))
    assert disagree == 0, f'REP{d}: circuit/analytic mismatch on {disagree} masks'
    for p in P_GRID:
        lfr = 0.0
        for mask in range(2 ** d):
            w = bin(mask).count('1')
            f = int(w > t)
            lfr += (p ** w) * ((1 - p) ** (d - w)) * f
        rows_l.append(dict(exp='rep_exact_lfr_v24', code=f'REP{d}', d=d, t=t,
                           p=p, lfr_exact=lfr, masks=2 ** d,
                           estimator='exact-enumeration-binomial',
                           seed=stable_seed('REP-EXACT', d)))
    print(f'REP{d}: {2**d} masks measured exhaustively; circuit==analytic on all')

for fname, rows in [('rep_exact_masks_v24.csv', rows_m),
                    ('rep_exact_lfr_v24.csv', rows_l)]:
    with open(OUT / fname, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader(); w.writerows(rows)
    print('Saved', fname, f'({len(rows)} rows)')
