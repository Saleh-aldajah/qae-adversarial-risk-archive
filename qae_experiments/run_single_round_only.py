"""
run_single_round_only.py  —  Single-round sweep: BP+OSD, MWPM-DEM, UF-BFS.

Reproduces:
  data/single_round_bposd_mwpm_dem.csv  (28 rows, BB72+BB144, 10,000 trials)
  data/single_round_all_codes.csv       (42 rows, BB72+BB144+BB288, 10,000 trials)
  data/single_round_uf_decoder.csv      (14 rows, BB72+BB144 UF-BFS, 10,000 trials)

All seeds use stable_seed() — SHA-256-derived, PYTHONHASHSEED-independent.
Shared helpers live in qae_utils.py / uf_bfs.py (v17 refactor; logic unchanged).
Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
import sys, csv, hashlib, math, time, itertools
from pathlib import Path
from collections import deque
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
OUT  = ROOT / "data"; OUT.mkdir(exist_ok=True)

from bb_codes import BB72, BB144, BB288, syn_from_mask, gf2_rref, in_rowspace
from decoders  import BpOsdDecoder, make_mwpm_dem, logical_fail, arr_to_mask, bernoulli_mask
from qae_utils import stable_seed, wilson95
from uf_bfs import build_adj, uf_decode

def syn_arr(s, n2):
    return np.array([(s>>i)&1 for i in range(n2)], dtype=np.uint8)

TRIALS = 10000
PS_STD = [0.001,0.002,0.004,0.006,0.008,0.010,0.012]

# ── Run 1: BP+OSD + MWPM-DEM on BB72 and BB144 ────────────────────────────
rows_28 = []
rows_42 = []

print("Single-round BP+OSD + MWPM-DEM  (BB72, BB144, BB288)")
for code, cname in [(BB72,'BB72'),(BB144,'BB144'),(BB288,'BB288')]:
    n, n2 = code['n'], code['n']//2
    HX_rref, HX_pivots = gf2_rref(code['HX'])
    HZ_rref, HZ_pivots = gf2_rref(code['HZ'])
    for dec_label, dec_type in [('BP+OSD','bposd'),('MWPM-DEM','mwpm')]:
        for p in PS_STD:
            seed = stable_seed(cname, dec_label, p)
            rng  = np.random.default_rng(seed); failures=0; t0=time.time()
            if dec_type=='bposd':
                dz=BpOsdDecoder(code['HX'],error_rate=p,bp_method='ms',
                    ms_scaling_factor=0.625,osd_method='osd_cs',osd_order=7,max_iter=100)
                dx=BpOsdDecoder(code['HZ'],error_rate=p,bp_method='ms',
                    ms_scaling_factor=0.625,osd_method='osd_cs',osd_order=7,max_iter=100)
            else:
                mz,mx=make_mwpm_dem(code['HX'],code['HZ'],n,n2,p)
            for _ in range(TRIALS):
                ez=bernoulli_mask(n,p,rng); ex=bernoulli_mask(n,p,rng)
                sz=syn_from_mask(ez,code['hx_cols']); sx=syn_from_mask(ex,code['hz_cols'])
                cz=arr_to_mask(dz.decode(syn_arr(sz,n2)) if dec_type=='bposd'
                               else mz.decode(syn_arr(sz,n2)))
                cx=arr_to_mask(dx.decode(syn_arr(sx,n2)) if dec_type=='bposd'
                               else mx.decode(syn_arr(sx,n2)))
                if logical_fail(ez^cz,ex^cx,code): failures+=1
            lo,hi=wilson95(failures,TRIALS)
            row=dict(exp='single_round',code=cname,decoder=dec_label,rounds=1,
                     p=p,trials=TRIALS,failures=failures,lfr=round(failures/TRIALS,6),
                     ci_lo=round(lo,6),ci_hi=round(hi,6),seed=seed,
                     hx_sha256=code['hx_sha'],hz_sha256=code['hz_sha'])
            rows_42.append(row)
            if cname in ('BB72','BB144'): rows_28.append(row)
            print(f"  {cname:6s} {dec_label:10s} p={p:.3f}: "
                  f"{failures:5d}/{TRIALS} [{lo:.5f},{hi:.5f}]  ({time.time()-t0:.0f}s)")

# ── Run 2: UF-BFS on BB72 and BB144 ──────────────────────────────────────
print("\nSingle-round UF-BFS  (BB72, BB144)")
rows_uf = []
for code, cname in [(BB72,'BB72'),(BB144,'BB144')]:
    n, n2 = code['n'], code['n']//2
    HX_rref,HX_pivots=gf2_rref(code['HX']); HZ_rref,HZ_pivots=gf2_rref(code['HZ'])
    adj_z=build_adj(code['HX'],n,n2); adj_x=build_adj(code['HZ'],n,n2)
    for p in PS_STD:
        seed=stable_seed('UF',cname,p)
        rng=np.random.default_rng(seed); failures=0; t0=time.time()
        for _ in range(TRIALS):
            ez=bernoulli_mask(n,p,rng); ex=bernoulli_mask(n,p,rng)
            sz=syn_from_mask(ez,code['hx_cols']); sx=syn_from_mask(ex,code['hz_cols'])
            cz=uf_decode(adj_z,sz,n2); cx=uf_decode(adj_x,sx,n2)
            rz=ez^cz; rx=ex^cx
            vz=np.array([(rz>>i)&1 for i in range(n)],dtype=np.uint8)
            vx=np.array([(rx>>i)&1 for i in range(n)],dtype=np.uint8)
            if not(in_rowspace(vz,HZ_rref,HZ_pivots) and
                   in_rowspace(vx,HX_rref,HX_pivots)): failures+=1
        lo,hi=wilson95(failures,TRIALS)
        rows_uf.append(dict(exp='single_round',code=cname,decoder='UF-BFS',rounds=1,
            p=p,trials=TRIALS,failures=failures,lfr=round(failures/TRIALS,6),
            ci_lo=round(lo,6),ci_hi=round(hi,6),seed=seed,
            hx_sha256=code['hx_sha'],hz_sha256=code['hz_sha']))
        print(f"  {cname:6s} UF-BFS    p={p:.3f}: {failures:5d}/{TRIALS} [{lo:.5f},{hi:.5f}]  ({time.time()-t0:.0f}s)")

# ── Save all three output files ───────────────────────────────────────────
for fname, rows in [
    ('single_round_bposd_mwpm_dem.csv', rows_28),
    ('single_round_all_codes.csv',      rows_42),
    ('single_round_uf_decoder.csv',     rows_uf),
]:
    with open(OUT/fname,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    print(f"\nSaved {fname}  ({len(rows)} rows)")
