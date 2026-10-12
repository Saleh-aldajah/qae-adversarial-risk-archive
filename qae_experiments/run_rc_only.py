"""
run_rc_only.py  —  Repeated-cycle BP+OSD for all three codes.

Reproduces:
  data/repeated_cycle_bposd.csv       (14 rows, BB72+BB144, 2,000 trials)
  data/repeated_cycle_bb288_bposd.csv  (7 rows, BB288, 500 trials)
  data/repeated_cycle_all_codes.csv   (21 rows merged)

Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
import sys, csv, hashlib, math, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
OUT  = ROOT / "data"; OUT.mkdir(exist_ok=True)

from bb_codes import BB72, BB144, BB288, syn_from_mask
from decoders  import BpOsdDecoder, logical_fail, arr_to_mask, bernoulli_mask
from qae_utils import stable_seed, wilson95

PS = [0.001,0.002,0.004,0.006,0.008,0.010,0.012]

def run_rc(code, cname, rounds, ps, trials):
    n, n2 = code['n'], code['n']//2
    rows = []; print(f"\n{cname}  (d={rounds} rounds, {trials} trials)")
    for p in ps:
        seed = stable_seed('RC', cname, p, rounds)
        rng  = np.random.default_rng(seed); failures=0; t0=time.time()
        Ir   = np.eye(rounds, dtype=np.uint8)
        nmc  = rounds*n2
        Hm   = np.zeros((rounds*n2, nmc), dtype=np.uint8)
        for r in range(rounds):
            for c2 in range(n2):
                Hm[r*n2+c2,r*n2+c2]=1
                if r+1<rounds: Hm[(r+1)*n2+c2,r*n2+c2]=1
        He_z = np.hstack([np.kron(Ir,code['HX']),Hm])
        He_x = np.hstack([np.kron(Ir,code['HZ']),Hm])
        cp   = np.array([p]*(rounds*n)+[p]*nmc)
        dz=BpOsdDecoder(He_z,error_rate=p,channel_probs=cp,bp_method='ms',
                        ms_scaling_factor=0.625,osd_method='osd_cs',osd_order=7,max_iter=100)
        dx=BpOsdDecoder(He_x,error_rate=p,channel_probs=cp,bp_method='ms',
                        ms_scaling_factor=0.625,osd_method='osd_cs',osd_order=7,max_iter=100)
        for _ in range(trials):
            cum_z=cum_x=0; szs=[]; sxs=[]
            for r in range(rounds):
                ez=(bernoulli_mask(n,p,rng) if r<rounds-1 else 0)
                ex=(bernoulli_mask(n,p,rng) if r<rounds-1 else 0)
                cum_z^=ez; cum_x^=ex
                sz=syn_from_mask(cum_z,code['hx_cols']); sx=syn_from_mask(cum_x,code['hz_cols'])
                if r<rounds-1:
                    for i in range(n2):
                        if rng.random()<p: sz^=(1<<i)
                        if rng.random()<p: sx^=(1<<i)
                szs.append(sz); sxs.append(sx)
            dtz=np.zeros(rounds*n2,dtype=np.uint8); dtx=np.zeros(rounds*n2,dtype=np.uint8)
            pz=px=0
            for r,(sz,sx) in enumerate(zip(szs,sxs)):
                d2z=sz^pz; d2x=sx^px
                for i in range(n2): dtz[r*n2+i]=(d2z>>i)&1; dtx[r*n2+i]=(d2x>>i)&1
                pz=sz; px=sx
            raw_z=dz.decode(dtz); raw_x=dx.decode(dtx)
            cz=np.zeros(n,dtype=np.uint8); cx=np.zeros(n,dtype=np.uint8)
            for r in range(rounds):
                for j in range(n): cz[j]^=raw_z[r*n+j]; cx[j]^=raw_x[r*n+j]
            if logical_fail(cum_z^arr_to_mask(cz),cum_x^arr_to_mask(cx),code): failures+=1
        lo,hi=wilson95(failures,trials)
        rows.append(dict(exp='repeated_cycle',code=cname,decoder='BP+OSD',rounds=rounds,
            p=p,trials=trials,failures=failures,lfr=round(failures/trials,6),
            ci_lo=round(lo,6),ci_hi=round(hi,6),seed=seed,
            hx_sha256=code['hx_sha'],hz_sha256=code['hz_sha']))
        print(f"  p={p:.3f}: {failures:4d}/{trials} [{lo:.5f},{hi:.5f}]  ({time.time()-t0:.0f}s)")
    return rows

rows_72_144 = run_rc(BB72, 'BB72', 6, PS, 2000) + run_rc(BB144, 'BB144', 12, PS, 2000)
rows_288    = run_rc(BB288, 'BB288', 18, PS, 500)
rows_all    = rows_72_144 + rows_288

for fname, rows in [
    ('repeated_cycle_bposd.csv',       rows_72_144),
    ('repeated_cycle_bb288_bposd.csv', rows_288),
    ('repeated_cycle_all_codes.csv',   rows_all),
]:
    with open(OUT/fname,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    print(f"Saved {fname}  ({len(rows)} rows)")
