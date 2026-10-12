#!/usr/bin/env python3
"""WS-A2 archive wire-in: sha256 manifest over all active-provenance artifacts +
manuscript-ready appendix text (Section AP) with the A/B result numbers."""
import os, json, hashlib, datetime, csv
import numpy as np
HERE = os.path.abspath(os.path.dirname(__file__))
RES  = os.path.join(HERE, 'results')

def sha256(p):
    h = hashlib.sha256()
    with open(p,'rb') as f:
        for chunk in iter(lambda: f.read(1<<20), b''): h.update(chunk)
    return h.hexdigest()

# ---------- 1. manifest ----------
manifest = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'scope': 'WS-A active provenance: defect maps, A/B line selection, IBM A/B run artifacts, equivalence certificate',
            'files': []}
for sub in ('results','counts','circuits','backend_snapshots','figures'):
    d = os.path.join(HERE, sub)
    if not os.path.isdir(d): continue
    for fn in sorted(os.listdir(d)):
        p = os.path.join(d, fn)
        if not os.path.isfile(p): continue
        manifest['files'].append({'path': f'active_provenance/{sub}/{fn}',
                                  'bytes': os.path.getsize(p), 'sha256': sha256(p)})
with open(os.path.join(HERE,'MANIFEST.json'),'w') as f:
    json.dump(manifest, f, indent=1)
print('manifest:', len(manifest['files']), 'files hashed')

# ---------- 2. statistics ----------
rows = list(csv.DictReader(open(os.path.join(RES,'ap_ab_results.csv'))))
detail = json.load(open(os.path.join(RES,'ap_ab_decode_detail.json')))
cmh_z = detail['cmh_z']
from math import erfc, sqrt
cmh_p_onesided = 0.5*erfc(abs(cmh_z)/sqrt(2)) * (1 if cmh_z<0 else -1)
# CMH pooled odds ratio
num = den = 0.0
totA_f = totA_s = totB_f = totB_s = 0
for r in rows:
    a,b = int(r['A_fail']), int(r['B_fail']); na,nb = int(r['A_shots']), int(r['B_shots'])
    n = na+nb; tf = a+b
    num += (a*(nb-b))/n; den += ((na-a)*b)/n
    totA_f+=a; totB_f+=b; totA_s+=na; totB_s+=nb
OR = num/den
print(f'CMH z={cmh_z:.3f}  one-sided p={cmh_p_onesided:.4f}  pooled OR(B vs A)={OR:.3f}')
print(f'pooled LER: A={totA_f}/{totA_s}={totA_f/totA_s:.5f}  B={totB_f}/{totB_s}={totB_f/totB_s:.5f}')

# REP5 detection-rate asymmetry (limitation disclosure)
det_z = {}
for cfg in ('REP5-X','REP5-Z'):
    A = np.array(detail['configs'][cfg]['A']['det']); B = np.array(detail['configs'][cfg]['B']['det'])
    pa, pb = A.mean(), B.mean(); n = 10000*A.size
    va = A.var(ddof=1)/A.size; vb = B.var(ddof=1)/B.size
    det_z[cfg] = (pb-pa)/np.sqrt((pa*(1-pa)+pb*(1-pb))/n)
print('detection-rate z (REP5):', {k:round(v,2) for k,v in det_z.items()})
