"""
run_e4_robustness.py  —  E4: decoder-hyperparameter robustness sweep.

BB72, single-round protocol identical to the archive runner. Sweep:
  OSD order in {0, 7, 20}  x  min-sum scaling in {0.5, 0.625}
at p in {0.004, 0.008, 0.012}, 10,000 trials per cell. BP+OSD only.

Seed: stable_seed('E4', osd_order, ms_scale, p).
Output: data/robustness_sweep_bb72.csv
Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
import sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from bb_codes import BB72, syn_from_mask
from decoders import BpOsdDecoder, logical_fail, arr_to_mask, bernoulli_mask
from qae_utils import stable_seed, wilson95, write_csv

TRIALS = 10000
PS = [0.004, 0.008, 0.012]
OSD_ORDERS = [0, 7, 20]
MS_SCALINGS = [0.5, 0.625]

code = BB72; cname = 'BB72'
n, n2 = code['n'], code['n']//2

def syn_arr(s):
    return np.array([(s >> i) & 1 for i in range(n2)], dtype=np.uint8)

rows = []
for order in OSD_ORDERS:
    for scale in MS_SCALINGS:
        for p in PS:
            seed = stable_seed('E4', order, scale, p)
            rng = np.random.default_rng(seed)
            dz = BpOsdDecoder(code['HX'], error_rate=p, bp_method='ms',
                              ms_scaling_factor=scale, osd_method='osd_cs',
                              osd_order=order, max_iter=100)
            dx = BpOsdDecoder(code['HZ'], error_rate=p, bp_method='ms',
                              ms_scaling_factor=scale, osd_method='osd_cs',
                              osd_order=order, max_iter=100)
            failures = 0; t0 = time.time()
            for _ in range(TRIALS):
                ez = bernoulli_mask(n, p, rng); ex = bernoulli_mask(n, p, rng)
                sz = syn_arr(syn_from_mask(ez, code['hx_cols']))
                sx = syn_arr(syn_from_mask(ex, code['hz_cols']))
                cz = arr_to_mask(dz.decode(sz))
                cx = arr_to_mask(dx.decode(sx))
                if logical_fail(ez ^ cz, ex ^ cx, code):
                    failures += 1
            lo, hi = wilson95(failures, TRIALS)
            rows.append(dict(exp='E4_robustness', code=cname,
                             decoder=f'BP+OSD(osd_cs-{order},ms-{scale})',
                             rounds=1, p=p, trials=TRIALS, failures=failures,
                             lfr=round(failures / TRIALS, 6),
                             ci_lo=round(lo, 6), ci_hi=round(hi, 6),
                             osd_order=order, ms_scale=scale, seed=seed,
                             hx_sha256=code['hx_sha'], hz_sha256=code['hz_sha']))
            print(f"  osd={order:2d} ms={scale:.3f} p={p:.3f}: "
                  f"{failures:5d}/{TRIALS} [{lo:.5f},{hi:.5f}] "
                  f"({time.time()-t0:.0f}s)", flush=True)

write_csv('robustness_sweep_bb72.csv', rows)
