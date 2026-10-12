#!/usr/bin/env python3
"""
run_e3_rc_fss.py  -  finite-size-scaling extension of the adaptive
repeated-cycle BP+OSD ladder (extends the archived grid upward in p to
locate the curve crossing required for a formal FSS collapse).

Identical spacetime construction, noise model, decoder settings, batch
discipline, and adaptive stopping rule as the archived adaptive ladder
(aligned-priors spacetime matrices; perfect final round; min-sum BP with
scaling 0.625; OSD-CS order 7; max_iter 100).  New elements only:
  * extended p grid {0.016, 0.020, 0.024, 0.028, 0.032}
  * independent seed stream under context 'E3fss'
  * per-batch JSONL checkpointing so partial cells survive interruption

Usage: python run_e3_rc_fss.py {bb72|bb144|bb288}
Output: repeated_cycle_fss_{code}.csv  (+ repeated_cycle_fss_{code}.ckpt.jsonl)
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from bb_codes import BB72, BB144, BB288, syn_from_mask
from decoders import BpOsdDecoder, logical_fail, arr_to_mask, bernoulli_mask
from qae_utils import stable_seed, wilson95
from run_rc_only_v24 import spacetime_matrices

CODES = {'bb72': (BB72, 6), 'bb144': (BB144, 12), 'bb288': (BB288, 18)}
import os
PS = ([float(x) for x in os.environ['FSS_GRID'].split(',')]
      if 'FSS_GRID' in os.environ
      else [0.016, 0.020, 0.024, 0.028, 0.032])
SUFFIX = os.environ.get('FSS_SUFFIX', '')
BATCH = 2_000
FAIL_STOP = 50
MODEL_REV = 'aligned-priors'
EXP = 'E3_rc_fss'

cname = sys.argv[1]
code, rounds = CODES[cname]
n, n2 = code['n'], code['n'] // 2

# Per-code adaptive budgets (pinned): bb288 decoding is ~60x slower per
# trial than bb144; its cells use a 6000-trial budget so that zero-failure
# cells still certify Wilson upper bounds <= 6.4e-4, tighter than the
# 20k-budget bound's relevance threshold for crossing detection.
MAX_TRIALS = 6_000 if cname == 'bb288' else 20_000

He_z, He_x = spacetime_matrices(code, rounds)

CKPT = ROOT / f'repeated_cycle_fss{SUFFIX}_{cname}.ckpt.jsonl'
OUT = ROOT / f'repeated_cycle_fss{SUFFIX}_{cname}.csv'


def run_batch(p, batch_idx, dz, dx):
    seed = stable_seed('E3fss', cname, p, rounds, batch_idx)
    rng = np.random.default_rng(seed)
    fails = 0
    for _ in range(BATCH):
        cum_z = cum_x = 0
        szs = []
        sxs = []
        for r in range(rounds):
            ez = (bernoulli_mask(n, p, rng) if r < rounds - 1 else 0)
            ex = (bernoulli_mask(n, p, rng) if r < rounds - 1 else 0)
            cum_z ^= ez
            cum_x ^= ex
            sz = syn_from_mask(cum_z, code['hx_cols'])
            sx = syn_from_mask(cum_x, code['hz_cols'])
            if r < rounds - 1:
                for i in range(n2):
                    if rng.random() < p:
                        sz ^= (1 << i)
                    if rng.random() < p:
                        sx ^= (1 << i)
            szs.append(sz)
            sxs.append(sx)
        dtz = np.zeros(rounds * n2, dtype=np.uint8)
        dtx = np.zeros(rounds * n2, dtype=np.uint8)
        pz = px = 0
        for r, (sz, sx) in enumerate(zip(szs, sxs)):
            d2z = sz ^ pz
            d2x = sx ^ px
            for i in range(n2):
                dtz[r * n2 + i] = (d2z >> i) & 1
                dtx[r * n2 + i] = (d2x >> i) & 1
            pz = sz
            px = sx
        raw_z = dz.decode(dtz)
        raw_x = dx.decode(dtx)
        cz = np.zeros(n, dtype=np.uint8)
        cx = np.zeros(n, dtype=np.uint8)
        for r in range(rounds - 1):
            for j in range(n):
                cz[j] ^= raw_z[r * n + j]
                cx[j] ^= raw_x[r * n + j]
        if logical_fail(cum_z ^ arr_to_mask(cz), cum_x ^ arr_to_mask(cx), code):
            fails += 1
    return seed, fails


def flush(rows):
    hdr = ('exp,code,decoder,rounds,p,trials,failures,lfr,ci_lo,ci_hi,seed,'
           'n_batches,batch_seeds,stop_reason,model_rev,hx_sha256,hz_sha256\n')
    with open(OUT, 'w') as f:
        f.write(hdr)
        for r in rows:
            f.write(','.join(str(r[k]) for k in hdr.strip().split(',')) + '\n')


# resume: skip completed cells
done = set()
if OUT.exists():
    for ln in OUT.read_text().splitlines()[1:]:
        if ln.strip():
            done.add(float(ln.split(',')[4]))

rows = []
if OUT.exists():
    import csv as _csv
    for r in _csv.DictReader(open(OUT)):
        rows.append(r)

for p in PS:
    if p in done:
        print(f'skip {cname} p={p} (done)', flush=True)
        continue
    cp = np.array([p] * ((rounds - 1) * n + (rounds - 1) * n2))
    kw = dict(error_rate=p, channel_probs=cp, bp_method='ms',
              ms_scaling_factor=0.625, osd_method='osd_cs', osd_order=7,
              max_iter=100)
    dz = BpOsdDecoder(He_z, **kw)
    dx = BpOsdDecoder(He_x, **kw)
    failures = 0
    trials = 0
    batch_idx = 0
    seeds = []
    t0 = time.time()
    while trials < MAX_TRIALS and (batch_idx == 0 or failures < FAIL_STOP):
        seed, fb = run_batch(p, batch_idx, dz, dx)
        seeds.append(seed)
        failures += fb
        trials += BATCH
        with open(CKPT, 'a') as f:
            f.write(json.dumps(dict(code=cname, p=p, batch=batch_idx,
                                    fails=fb, cum_fail=failures,
                                    cum_trials=trials, seed=seed)) + '\n')
        print(f'  {cname} p={p} batch {batch_idx}: +{fb} fails '
              f'(total {failures}/{trials})  ({time.time()-t0:.0f}s)',
              flush=True)
        batch_idx += 1
    lo, hi = wilson95(failures, trials)
    stop = ('>=50 failures' if failures >= FAIL_STOP
            else f'budget {MAX_TRIALS}')
    rows.append(dict(exp=EXP, code=cname, decoder='BP+OSD', rounds=rounds,
                     p=p, trials=trials, failures=failures,
                     lfr=round(failures / trials, 6), ci_lo=round(lo, 6),
                     ci_hi=round(hi, 6), seed=seeds[0], n_batches=batch_idx,
                     batch_seeds=';'.join(map(str, seeds)), stop_reason=stop,
                     model_rev=MODEL_REV, hx_sha256=code['hx_sha'],
                     hz_sha256=code['hz_sha']))
    flush(rows)
    print(f'DONE {cname} p={p}: {failures}/{trials} [{lo:.5f},{hi:.5f}] '
          f'stop={stop} ({time.time()-t0:.0f}s)', flush=True)

print(f'ALL DONE {cname}', flush=True)
