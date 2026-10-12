"""
run_e1_rare_event.py  —  E1: rare-event BP+OSD at 10^6 trials/point.

Single-round protocol identical to the archive runner
(run_single_round_only.py), extended to 1,000,000 trials at
p in {0.002, 0.004} for BB72, BB144, BB288. BP+OSD only.

Seed: stable_seed('E1', code, p).
Output: data/rare_event_bposd.csv
Zero-failure rows are flagged in the 'note' column; the manuscript table
reports the one-sided Wilson 95% upper bound for those rows.

Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
import sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from bb_codes import BB72, BB144, BB288, syn_from_mask
from decoders import BpOsdDecoder, logical_fail, arr_to_mask, bernoulli_mask
from qae_utils import stable_seed, wilson95, wilson_one_sided_upper, write_csv

TRIALS = 1_000_000
PS = [0.002, 0.004]

def syn_arr(s, n2):
    return np.array([(s >> i) & 1 for i in range(n2)], dtype=np.uint8)

rows = []
for code, cname in [(BB72, 'BB72'), (BB144, 'BB144'), (BB288, 'BB288')]:
    n, n2 = code['n'], code['n']//2
    for p in PS:
        seed = stable_seed('E1', cname, p)
        rng = np.random.default_rng(seed)
        dz = BpOsdDecoder(code['HX'], error_rate=p, bp_method='ms',
                          ms_scaling_factor=0.625, osd_method='osd_cs',
                          osd_order=7, max_iter=100)
        dx = BpOsdDecoder(code['HZ'], error_rate=p, bp_method='ms',
                          ms_scaling_factor=0.625, osd_method='osd_cs',
                          osd_order=7, max_iter=100)
        failures = 0
        t0 = time.time()
        for t in range(TRIALS):
            ez = bernoulli_mask(n, p, rng)
            ex = bernoulli_mask(n, p, rng)
            sz = syn_from_mask(ez, code['hx_cols'])
            sx = syn_from_mask(ex, code['hz_cols'])
            cz = arr_to_mask(dz.decode(syn_arr(sz, n2)))
            cx = arr_to_mask(dx.decode(syn_arr(sx, n2)))
            if logical_fail(ez ^ cz, ex ^ cx, code):
                failures += 1
            if (t + 1) % 100_000 == 0:
                el = time.time() - t0
                print(f"  {cname} p={p}: {t+1}/{TRIALS} fails={failures} "
                      f"({el:.0f}s, eta {el/(t+1)*(TRIALS-t-1):.0f}s)", flush=True)
        lo, hi = wilson95(failures, TRIALS)
        note = ('zero failures observed; report one-sided 95% Wilson upper '
                f'{wilson_one_sided_upper(0, TRIALS):.3e}' if failures == 0
                else '')
        rows.append(dict(exp='E1_rare_event', code=cname, decoder='BP+OSD',
                         rounds=1, p=p, trials=TRIALS, failures=failures,
                         lfr=failures / TRIALS,
                         ci_lo=lo, ci_hi=hi,
                         one_sided_upper=round(wilson_one_sided_upper(failures, TRIALS), 10),
                         seed=seed, hx_sha256=code['hx_sha'],
                         hz_sha256=code['hz_sha'], note=note))
        print(f"DONE {cname} p={p}: {failures}/{TRIALS}  "
              f"[{lo:.3e},{hi:.3e}]  ({time.time()-t0:.0f}s)", flush=True)

write_csv('rare_event_bposd.csv', rows)
