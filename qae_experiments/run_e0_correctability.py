"""
run_e0_correctability.py  —  E0: per-weight correctability contrast (BB72).

For every binary Z-error pattern of weight w <= 2 (exhaustive:
1 + 72 + C(72,2) = 2,629 patterns) and 2,000 sampled weight-3 patterns,
measure whether each decoder returns a correction whose residual is a
Z-stabilizer (in the rowspace of HZ):

  decoders: MWPM-DEM (DEM-chain graphification), UF-BFS,
            radius-2 lookup (certified reference),
            BP-guided matching (E6) if available.

The sampled weight-3 set is SHARED across decoders (paired contrast);
sampling stream seed = stable_seed('E0', code, 'sample', w).

Output: data/correctability_by_weight.csv
Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
import sys, itertools, time
from pathlib import Path
from math import comb
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from bb_codes import BB72, syn_from_mask, gf2_rref, in_rowspace
from decoders import make_mwpm_dem, arr_to_mask
from qae_utils import stable_seed, wilson95, build_lookup, write_csv
from uf_bfs import build_adj, uf_decode

code = BB72
n, n2 = code['n'], code['n']//2
cname = 'BB72'
HZ_rref, HZ_pivots = code['HZ_rref'], code['HZ_pivots']

P_REF = 0.004  # graph structure is p-independent (uniform edge weights);
               # boundary factor is a uniform 100x scale -> decode invariant.

def syn_arr(s):
    return np.array([(s >> i) & 1 for i in range(n2)], dtype=np.uint8)

def residual_ok(e, c):
    r = e ^ c
    v = np.array([(r >> i) & 1 for i in range(n)], dtype=np.uint8)
    return in_rowspace(v, HZ_rref, HZ_pivots)

# ── pattern sets ─────────────────────────────────────────────────────────
patterns = {0: [0]}
for w in (1, 2):
    patterns[w] = [sum(1 << j for j in cb) for cb in itertools.combinations(range(n), w)]

SAMPLE_W3 = 2000
seed_w3 = stable_seed('E0', cname, 'sample', 3)
rng = np.random.default_rng(seed_w3)
total_w3 = comb(n, 3)
idxs = np.sort(rng.choice(total_w3, size=SAMPLE_W3, replace=False))
combos = list(itertools.combinations(range(n), 3))
patterns[3] = [sum(1 << j for j in combos[i]) for i in idxs]
print(f"weight-3 sample: {SAMPLE_W3} of {total_w3} patterns, seed {seed_w3}")

# ── decoders ─────────────────────────────────────────────────────────────
mz, _mx = make_mwpm_dem(code['HX'], code['HZ'], n, n2, P_REF)
adj_z = build_adj(code['HX'], n, n2)
lookup_z = build_lookup(code['hx_cols'], n, 2)

def dec_mwpm(sz):
    return arr_to_mask(mz.decode(syn_arr(sz)))

def dec_uf(sz):
    return uf_decode(adj_z, sz, n2)

def dec_lookup(sz):
    c = lookup_z.get(sz, None)
    return c if c is not None else None   # None = outside certified radius

DECODERS = [('MWPM-DEM', dec_mwpm), ('UF-BFS', dec_uf),
            ('radius-2 lookup', dec_lookup)]

# Optional E6 decoder: BP-guided matching (only if run_e6 module present)
try:
    from bp_guided import make_bpgm_decoder
    dec_bpgm = make_bpgm_decoder(code, P_REF)
    DECODERS.append(('BP-guided MWPM', dec_bpgm))
    print("E6 decoder available: including BP-guided MWPM in contrast")
except ImportError:
    print("E6 decoder not present: contrast limited to MWPM-DEM/UF-BFS/lookup")

# ── run ──────────────────────────────────────────────────────────────────
rows = []
t0 = time.time()
for dname, dfn in DECODERS:
    for w in (0, 1, 2, 3):
        fails = 0
        tested = 0
        for e in patterns[w]:
            sz = syn_from_mask(e, code['hx_cols'])
            c = dfn(sz)
            tested += 1
            if c is None or not residual_ok(e, c):
                fails += 1
        lo, hi = wilson95(fails, tested)
        rows.append(dict(
            exp='E0_correctability', code=cname, decoder=dname, weight=w,
            scope='exhaustive' if w <= 2 else f'sampled-{SAMPLE_W3}',
            patterns_tested=tested, failures=fails,
            failure_rate=round(fails / tested, 6),
            correct=tested - fails,
            correctability=round((tested - fails) / tested, 6),
            ci_lo=round(lo, 6), ci_hi=round(hi, 6),
            seed=seed_w3 if w == 3 else stable_seed('E0', cname, 'exact', w),
            hx_sha256=code['hx_sha'], hz_sha256=code['hz_sha']))
        print(f"  {dname:16s} w={w}: fails {fails:5d}/{tested}  "
              f"correctability {(tested-fails)/tested:.4f}  ({time.time()-t0:.0f}s)")

write_csv('correctability_by_weight.csv', rows)
