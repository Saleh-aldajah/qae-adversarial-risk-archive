
import sys; sys.path.insert(0,".")
import numpy as np, time
from bb_codes import BB144, syn_from_mask
from decoders import BpOsdDecoder, logical_fail, arr_to_mask, bernoulli_mask
from qae_utils import stable_seed
code=BB144; rounds=12; n=code['n']; n2=n//2; p=0.012
Ir=np.eye(rounds,dtype=np.uint8); nmc=rounds*n2
Hm=np.zeros((rounds*n2,nmc),dtype=np.uint8)
for r in range(rounds):
    for c2 in range(n2):
        Hm[r*n2+c2,r*n2+c2]=1
        if r+1<rounds: Hm[(r+1)*n2+c2,r*n2+c2]=1
He_z=np.hstack([np.kron(Ir,code['HX']),Hm]); He_x=np.hstack([np.kron(Ir,code['HZ']),Hm])
cp=np.array([p]*(rounds*n)+[p]*nmc)
dz=BpOsdDecoder(He_z,error_rate=p,channel_probs=cp,bp_method='ms',ms_scaling_factor=0.625,osd_method='osd_cs',osd_order=7,max_iter=100)
dx=BpOsdDecoder(He_x,error_rate=p,channel_probs=cp,bp_method='ms',ms_scaling_factor=0.625,osd_method='osd_cs',osd_order=7,max_iter=100)
tot=0
for b in range(10):
    rng=np.random.default_rng(stable_seed('E3','BB144',p,rounds,b)); fails=0
    for _ in range(2000):
        cum_z=cum_x=0; szs=[];sxs=[]
        for r in range(rounds):
            ez=(bernoulli_mask(n,p,rng) if r<rounds-1 else 0); ex=(bernoulli_mask(n,p,rng) if r<rounds-1 else 0)
            cum_z^=ez; cum_x^=ex
            sz=syn_from_mask(cum_z,code['hx_cols']); sx=syn_from_mask(cum_x,code['hz_cols'])
            if r<rounds-1:
                for i in range(n2):
                    if rng.random()<p: sz^=(1<<i)
                    if rng.random()<p: sx^=(1<<i)
            szs.append(sz); sxs.append(sx)
        dtz=np.zeros(rounds*n2,dtype=np.uint8); dtx=np.zeros(rounds*n2,dtype=np.uint8); pz=px=0
        for r,(sz,sx) in enumerate(zip(szs,sxs)):
            d2z=sz^pz; d2x=sx^px
            for i in range(n2):
                dtz[r*n2+i]=(d2z>>i)&1; dtx[r*n2+i]=(d2x>>i)&1
            pz=sz; px=sx
        rz=dz.decode(dtz); rx=dx.decode(dtx)
        cz=np.zeros(n,dtype=np.uint8); cx=np.zeros(n,dtype=np.uint8)
        for r in range(rounds):
            for j in range(n): cz[j]^=rz[r*n+j]; cx[j]^=rx[r*n+j]
        if logical_fail(cum_z^arr_to_mask(cz), cum_x^arr_to_mask(cx), code): fails+=1
    tot+=fails
    print(f"batch {b}: +{fails} (total {tot}/{(b+1)*2000})", flush=True)
print("VERIFY BB144 p=0.012 total:", tot, "archived: 14", "MATCH" if tot==14 else "MISMATCH")
