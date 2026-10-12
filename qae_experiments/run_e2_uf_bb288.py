"""
run_e2_uf_bb288.py  —  E2: complete the missing UF-BFS row for BB288.

Protocol identical to the archive UF-BFS runner (run_single_round_only.py
Run 2): 7 p values x 10,000 trials, seed = stable_seed('UF', code, p).

Output: data/single_round_uf_bb288.csv
Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
import sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from bb_codes import BB288, syn_from_mask, in_rowspace
from decoders import bernoulli_mask
from qae_utils import stable_seed, write_csv, mc_row
from uf_bfs import build_adj, uf_decode

TRIALS = 10000
PS = [0.001, 0.002, 0.004, 0.006, 0.008, 0.010, 0.012]

code = BB288
cname = 'BB288'
n, n2 = code['n'], code['n']//2
HZ_rref, HZ_pivots = code['HZ_rref'], code['HZ_pivots']
HX_rref, HX_pivots = code['HX_rref'], code['HX_pivots']
adj_z = build_adj(code['HX'], n, n2)
adj_x = build_adj(code['HZ'], n, n2)

rows = []
for p in PS:
    seed = stable_seed('UF', cname, p)
    rng = np.random.default_rng(seed)
    failures = 0; t0 = time.time()
    for _ in range(TRIALS):
        ez = bernoulli_mask(n, p, rng); ex = bernoulli_mask(n, p, rng)
        sz = syn_from_mask(ez, code['hx_cols']); sx = syn_from_mask(ex, code['hz_cols'])
        cz = uf_decode(adj_z, sz, n2); cx = uf_decode(adj_x, sx, n2)
        rz = ez ^ cz; rx = ex ^ cx
        vz = np.array([(rz >> i) & 1 for i in range(n)], dtype=np.uint8)
        vx = np.array([(rx >> i) & 1 for i in range(n)], dtype=np.uint8)
        if not (in_rowspace(vz, HZ_rref, HZ_pivots) and
                in_rowspace(vx, HX_rref, HX_pivots)):
            failures += 1
    row = mc_row('single_round', code, cname, 'UF-BFS', 1, p, TRIALS, failures, seed)
    rows.append(row)
    print(f"  {cname} UF-BFS p={p:.3f}: {failures:5d}/{TRIALS} "
          f"[{row['ci_lo']:.5f},{row['ci_hi']:.5f}]  ({time.time()-t0:.0f}s)", flush=True)

write_csv('single_round_uf_bb288.csv', rows)
