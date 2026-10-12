"""
run_hardware_ablations.py  —  Controlled noise-component ablation study.

Reproduces:
  data/hardware_ablations.csv (8 rows, BB72, 3,000 trials per condition)
  data/hardware_three_condition_comparison.csv (15 rows, 5,000 trials)

These are simulation-model ablations, not causal real-hardware experiments.
Contributions attributed here reflect specified noise-model parameters only.
Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
import sys, csv, hashlib, math, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
OUT  = ROOT / "data"; OUT.mkdir(exist_ok=True)

from bb_codes import BB72, syn_from_mask, gf2_rref, in_rowspace
from decoders  import BpOsdDecoder, arr_to_mask, bernoulli_mask
from qae_utils import stable_seed, wilson95, build_lookup

code = BB72; n, n2 = code['n'], code['n']//2
HX_rref, HX_pivots = gf2_rref(code['HX'])
HZ_rref, HZ_pivots = gf2_rref(code['HZ'])

# Build radius-2 lookup tables (no external deps; build_lookup in qae_utils)
lz = build_lookup(code['hx_cols'], n, 2)
lx = build_lookup(code['hz_cols'], n, 2)

def decode_success(ez, ex, sz, sx):
    cz = lz.get(sz, 0); cx = lx.get(sx, 0)
    rz = ez^cz; rx = ex^cx
    vz = np.array([(rz>>i)&1 for i in range(n)],dtype=np.uint8)
    vx = np.array([(rx>>i)&1 for i in range(n)],dtype=np.uint8)
    return (in_rowspace(vz,HZ_rref,HZ_pivots) and in_rowspace(vx,HX_rref,HX_pivots))

import math as _m
T1_CZ,T2_CZ,TG_CZ = 150.0,100.0,0.2
T1_MS,T2_MS,TG_MS = 1e6,5e6,50.0
P_BASE = 5e-4
SWAP_FRAC = (96/n)*P_BASE
p_dec_cz = ((1-_m.exp(-TG_CZ/T1_CZ))+(1-_m.exp(-TG_CZ/T2_CZ)))/2
p_dec_ms = ((1-_m.exp(-TG_MS/T1_MS))+(1-_m.exp(-TG_MS/T2_MS)))/2

ABLATIONS = [
    ('Phenomenological',        P_BASE,             P_BASE*0.05, P_BASE),
    ('CZ: full model',          P_BASE+p_dec_cz+SWAP_FRAC, P_BASE*0.05, P_BASE),
    ('CZ: no SWAP',             P_BASE+p_dec_cz,    P_BASE*0.05, P_BASE),
    ('CZ: no idle noise',       P_BASE+p_dec_cz+SWAP_FRAC, 0.0, P_BASE),
    ('CZ: no meas noise',       P_BASE+p_dec_cz+SWAP_FRAC, P_BASE*0.05, 0.0),
    ('CZ: gate decoherence only', p_dec_cz,         0.0, 0.0),
    ('MS: full model',          P_BASE+p_dec_ms,    P_BASE*0.05, P_BASE),
    ('MS: CZ-matched gate',     P_BASE+p_dec_cz,    P_BASE*0.05, P_BASE),
]
T_ABL = 3000

rows_abl = []
print("Hardware ablations (simulation-model only)")
for label, p_data, p_idle, p_meas in ABLATIONS:
    seed=stable_seed('ABL', label, P_BASE)
    rng=np.random.default_rng(seed); failures=0; t0=time.time()
    for _ in range(T_ABL):
        ez=bernoulli_mask(n,p_data,rng); ex=bernoulli_mask(n,p_data,rng)
        ez^=bernoulli_mask(n,p_idle,rng); ex^=bernoulli_mask(n,p_idle,rng)
        sz=syn_from_mask(ez,code['hx_cols']); sx=syn_from_mask(ex,code['hz_cols'])
        for i in range(n2):
            if rng.random()<p_meas: sz^=(1<<i)
            if rng.random()<p_meas: sx^=(1<<i)
        if not decode_success(ez,ex,sz,sx): failures+=1
    lo,hi=wilson95(failures,T_ABL)
    rows_abl.append(dict(condition=label,p_base=P_BASE,trials=T_ABL,
        failures=failures,lfr=round(failures/T_ABL,6),ci_lo=round(lo,6),ci_hi=round(hi,6),
        seed=seed,p_eff_data=round(p_data,8),p_idle=round(p_idle,8),p_meas=round(p_meas,8),
        note='simulation-model only'))
    print(f"  {label:<32} {failures:5d}/{T_ABL}  [{lo:.5f},{hi:.5f}]  ({time.time()-t0:.0f}s)")

# Three-condition comparison at 5 p-values
print("\nThree-condition comparison (CZ, MS, Pheno)")
PS_HW = [5e-4, 1e-3, 2e-3, 3e-3, 5e-3]
T_HW = 5000
rows_hw = []
for cname, p_data_fn, note in [
    ('Phenomenological', lambda p: p, 'ideal'),
    ('CZ', lambda p: p+p_dec_cz+SWAP_FRAC, 'T1=150us,T2=100us,tg=0.2us'),
    ('MS', lambda p: p+p_dec_ms, 'T1=1Ms,T2=5Ms,tg=50us'),
]:
    for p in PS_HW:
        p_eff = min(1.0, p_data_fn(p))
        seed=stable_seed('HW3',cname,p)
        rng=np.random.default_rng(seed); failures=0
        for _ in range(T_HW):
            ez=bernoulli_mask(n,p_eff,rng); ex=bernoulli_mask(n,p_eff,rng)
            sz=syn_from_mask(ez,code['hx_cols']); sx=syn_from_mask(ex,code['hz_cols'])
            if not decode_success(ez,ex,sz,sx): failures+=1
        lo,hi=wilson95(failures,T_HW)
        rows_hw.append(dict(backend=cname,p=p,p_eff=round(p_eff,8),trials=T_HW,
            failures=failures,lfr=round(failures/T_HW,6),ci_lo=round(lo,6),
            ci_hi=round(hi,6),seed=seed,note=note))
        print(f"  {cname:20s} p={p:.0e}: {failures:5d}/{T_HW}  [{lo:.5f},{hi:.5f}]")

for fname, rows in [
    ('hardware_ablations.csv', rows_abl),
    ('hardware_three_condition_comparison.csv', rows_hw),
]:
    with open(OUT/fname,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    print(f"Saved {fname}")
