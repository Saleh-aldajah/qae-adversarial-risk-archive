"""
run_e5_crosscheck.py  —  E5: independent-path cross-check (BB72).

A FRESH single-round simulator written independently of the archive
runner logic:
  - errors drawn as vectorized numpy Bernoulli arrays (not bit-mask loops)
  - syndrome computed by direct GF(2) matrix product s = H e (mod 2)
    (not the packed-column XOR trick)
  - decoded with ldpc BP+OSD (same published config)
  - RNG stream deliberately disjoint: seed = (stable_seed('E5X', code, p)
    + 10**9) mod 2**32

Exact agreement with the archive CSVs is NOT expected (different streams);
the check is Wilson-CI overlap against data/single_round_all_codes.csv.

Output: data/crosscheck_e5.csv  (fresh + archived rows side by side)
Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
import csv as csvmod
import sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from bb_codes import BB72, in_rowspace
from decoders import BpOsdDecoder
from qae_utils import stable_seed, wilson95, write_csv

TRIALS = 10000
PS = [0.004, 0.008, 0.012]

code = BB72; cname = 'BB72'
n = code['n']
HX = code['HX'].astype(np.uint8); HZ = code['HZ'].astype(np.uint8)
HZ_rref, HZ_pivots = code['HZ_rref'], code['HZ_pivots']
HX_rref, HX_pivots = code['HX_rref'], code['HX_pivots']

rows = []
print("E5 fresh-path runs")
for p in PS:
    base = stable_seed('E5X', cname, p)
    seed = (base + 10**9) % 2**32
    rng = np.random.default_rng(seed)
    dz = BpOsdDecoder(HX, error_rate=p, bp_method='ms',
                      ms_scaling_factor=0.625, osd_method='osd_cs',
                      osd_order=7, max_iter=100)
    dx = BpOsdDecoder(HZ, error_rate=p, bp_method='ms',
                      ms_scaling_factor=0.625, osd_method='osd_cs',
                      osd_order=7, max_iter=100)
    failures = 0; t0 = time.time()
    for _ in range(TRIALS):
        ez = (rng.random(n) < p).astype(np.uint8)
        ex = (rng.random(n) < p).astype(np.uint8)
        sz = (HX @ ez) % 2          # direct GF(2) parity-check syndrome
        sx = (HZ @ ex) % 2
        cz = dz.decode(sz).astype(np.uint8) % 2
        cx = dx.decode(sx).astype(np.uint8) % 2
        rz = (ez + cz) % 2
        rx = (ex + cx) % 2
        if not (in_rowspace(rz, HZ_rref, HZ_pivots) and
                in_rowspace(rx, HX_rref, HX_pivots)):
            failures += 1
    lo, hi = wilson95(failures, TRIALS)
    rows.append(dict(exp='E5_crosscheck', path='fresh', code=cname,
                     decoder='BP+OSD', rounds=1, p=p, trials=TRIALS,
                     failures=failures, lfr=round(failures / TRIALS, 6),
                     ci_lo=round(lo, 6), ci_hi=round(hi, 6), seed=seed,
                     seed_base=base,
                     hx_sha256=code['hx_sha'], hz_sha256=code['hz_sha']))
    print(f"  fresh   p={p:.3f}: {failures:5d}/{TRIALS} [{lo:.5f},{hi:.5f}] "
          f"seed={seed} ({time.time()-t0:.0f}s)", flush=True)

# Side-by-side archive rows for the same cells + CI-overlap verdict
print("archive reference rows (data/single_round_all_codes.csv)")
with open(ROOT / 'data' / 'single_round_all_codes.csv', newline='') as f:
    for r in csvmod.DictReader(f):
        if r['code'] == cname and r['decoder'] == 'BP+OSD' and float(r['p']) in PS:
            fr = next(x for x in rows if x['path'] == 'fresh' and x['p'] == float(r['p']))
            overlap = not (float(r['ci_hi']) < fr['ci_lo'] or fr['ci_hi'] < float(r['ci_lo']))
            rows.append(dict(exp='E5_crosscheck', path='archive', code=cname,
                             decoder='BP+OSD', rounds=1, p=float(r['p']),
                             trials=int(r['trials']), failures=int(r['failures']),
                             lfr=float(r['lfr']), ci_lo=float(r['ci_lo']),
                             ci_hi=float(r['ci_hi']), seed=int(r['seed']),
                             seed_base='',
                             hx_sha256=r['hx_sha256'], hz_sha256=r['hz_sha256']))
            print(f"  archive p={float(r['p']):.3f}: {r['failures']:>5s}/{r['trials']} "
                  f"[{r['ci_lo']},{r['ci_hi']}] seed={r['seed']}  "
                  f"CI-overlap={'YES' if overlap else 'NO'}")

write_csv('crosscheck_e5.csv', rows)
