"""
run_e6_bp_guided.py  —  E6: BP-guided matching vs naive MWPM-DEM (BB72).

Paired comparison on ONE shared error stream per p: each trial is decoded
by both BP-guided MWPM (bp_guided.BpGuidedMwpm, see METHODS_APPENDIX) and
naive MWPM-DEM (uniform weights, decoders.make_mwpm_dem). Single-round
protocol identical to the archive runner (Z and X sides both decoded).

Seed: stable_seed('E6', code, p).
Output: data/bp_guided_matching_bb72.csv
Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
import sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from bb_codes import BB72, syn_from_mask
from decoders import logical_fail, arr_to_mask, bernoulli_mask, make_mwpm_dem
from bp_guided import BpGuidedMwpm
from qae_utils import stable_seed, write_csv, mc_row

TRIALS = 10000
PS = [0.004, 0.008, 0.012]

code = BB72; cname = 'BB72'
n, n2 = code['n'], code['n']//2

def syn_arr(s):
    return np.array([(s >> i) & 1 for i in range(n2)], dtype=np.uint8)

rows = []
for p in PS:
    seed = stable_seed('E6', cname, p)
    rng = np.random.default_rng(seed)
    gz = BpGuidedMwpm(code['HX'], p)   # Z errors, HX syndrome
    gx = BpGuidedMwpm(code['HZ'], p)   # X errors, HZ syndrome
    mz, mx = make_mwpm_dem(code['HX'], code['HZ'], n, n2, p)
    fails = {'BP-guided MWPM': 0, 'MWPM-DEM': 0}
    t0 = time.time()
    for _ in range(TRIALS):
        ez = bernoulli_mask(n, p, rng); ex = bernoulli_mask(n, p, rng)
        sz = syn_from_mask(ez, code['hx_cols']); sx = syn_from_mask(ex, code['hz_cols'])
        # BP-guided
        cz = gz.decode_mask(sz); cx = gx.decode_mask(sx)
        if logical_fail(ez ^ cz, ex ^ cx, code):
            fails['BP-guided MWPM'] += 1
        # naive MWPM-DEM on the same shot
        cz = arr_to_mask(mz.decode(syn_arr(sz)))
        cx = arr_to_mask(mx.decode(syn_arr(sx)))
        if logical_fail(ez ^ cz, ex ^ cx, code):
            fails['MWPM-DEM'] += 1
    for dname in ('BP-guided MWPM', 'MWPM-DEM'):
        row = mc_row('E6_bp_guided', code, cname, dname, 1, p, TRIALS,
                     fails[dname], seed)
        rows.append(row)
        print(f"  {dname:16s} p={p:.3f}: {fails[dname]:5d}/{TRIALS} "
              f"[{row['ci_lo']:.5f},{row['ci_hi']:.5f}]  ({time.time()-t0:.0f}s)",
              flush=True)

write_csv('bp_guided_matching_bb72.csv', rows)
