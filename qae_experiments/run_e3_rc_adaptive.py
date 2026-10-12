"""
run_e3_rc_adaptive.py  —  E3: repeated-cycle BP+OSD with adequate budgets.

Protocol identical to run_rc_only.py (d rounds per code, perfect final
round, detector differences, spacetime BP+OSD), but with an adaptive
stopping rule per row:
    run in 2,000-trial batches; stop after a batch when
    observed failures >= 50 OR total trials == 20,000.

Batch seeds: stable_seed('E3', code, p, rounds, batch_index), so every
batch is independently reproducible. 'trials' records trials actually used.

Usage: run_e3_rc_adaptive.py BB72|BB144|BB288   (one code per process)
Output: data/repeated_cycle_adaptive_<code>.csv

Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
import sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from bb_codes import BB72, BB144, BB288, syn_from_mask
from decoders import BpOsdDecoder, logical_fail, arr_to_mask, bernoulli_mask
from qae_utils import stable_seed, wilson95, write_csv

CODES = {'BB72': (BB72, 6), 'BB144': (BB144, 12), 'BB288': (BB288, 18)}
PS = [0.004, 0.006, 0.008, 0.012]
BATCH = 2_000
MAX_TRIALS = 20_000
FAIL_STOP = 50

cname = sys.argv[1]
code, rounds = CODES[cname]
n, n2 = code['n'], code['n']//2

# Spacetime check matrix (identical construction to run_rc_only.py)
Ir = np.eye(rounds, dtype=np.uint8)
nmc = rounds * n2
Hm = np.zeros((rounds * n2, nmc), dtype=np.uint8)
for r in range(rounds):
    for c2 in range(n2):
        Hm[r * n2 + c2, r * n2 + c2] = 1
        if r + 1 < rounds:
            Hm[(r + 1) * n2 + c2, r * n2 + c2] = 1
He_z = np.hstack([np.kron(Ir, code['HX']), Hm])
He_x = np.hstack([np.kron(Ir, code['HZ']), Hm])

def run_batch(p, batch_idx, dz, dx):
    seed = stable_seed('E3', cname, p, rounds, batch_idx)
    rng = np.random.default_rng(seed)
    fails = 0
    for _ in range(BATCH):
        cum_z = cum_x = 0
        szs = []; sxs = []
        for r in range(rounds):
            ez = (bernoulli_mask(n, p, rng) if r < rounds - 1 else 0)
            ex = (bernoulli_mask(n, p, rng) if r < rounds - 1 else 0)
            cum_z ^= ez; cum_x ^= ex
            sz = syn_from_mask(cum_z, code['hx_cols'])
            sx = syn_from_mask(cum_x, code['hz_cols'])
            if r < rounds - 1:
                for i in range(n2):
                    if rng.random() < p: sz ^= (1 << i)
                    if rng.random() < p: sx ^= (1 << i)
            szs.append(sz); sxs.append(sx)
        dtz = np.zeros(rounds * n2, dtype=np.uint8)
        dtx = np.zeros(rounds * n2, dtype=np.uint8)
        pz = px = 0
        for r, (sz, sx) in enumerate(zip(szs, sxs)):
            d2z = sz ^ pz; d2x = sx ^ px
            for i in range(n2):
                dtz[r * n2 + i] = (d2z >> i) & 1
                dtx[r * n2 + i] = (d2x >> i) & 1
            pz = sz; px = sx
        raw_z = dz.decode(dtz); raw_x = dx.decode(dtx)
        cz = np.zeros(n, dtype=np.uint8); cx = np.zeros(n, dtype=np.uint8)
        for r in range(rounds):
            for j in range(n):
                cz[j] ^= raw_z[r * n + j]; cx[j] ^= raw_x[r * n + j]
        if logical_fail(cum_z ^ arr_to_mask(cz), cum_x ^ arr_to_mask(cx), code):
            fails += 1
    return seed, fails

rows = []
for p in PS:
    cp = np.array([p] * (rounds * n) + [p] * nmc)
    dz = BpOsdDecoder(He_z, error_rate=p, channel_probs=cp, bp_method='ms',
                      ms_scaling_factor=0.625, osd_method='osd_cs',
                      osd_order=7, max_iter=100)
    dx = BpOsdDecoder(He_x, error_rate=p, channel_probs=cp, bp_method='ms',
                      ms_scaling_factor=0.625, osd_method='osd_cs',
                      osd_order=7, max_iter=100)
    failures = 0; trials = 0; batch_idx = 0; seeds = []
    t0 = time.time()
    while trials < MAX_TRIALS and (batch_idx == 0 or failures < FAIL_STOP):
        seed, fb = run_batch(p, batch_idx, dz, dx)
        seeds.append(seed)
        failures += fb; trials += BATCH
        print(f"  {cname} p={p} batch {batch_idx}: +{fb} fails "
              f"(total {failures}/{trials})  ({time.time()-t0:.0f}s)", flush=True)
        batch_idx += 1
    lo, hi = wilson95(failures, trials)
    stop = ('>=50 failures' if failures >= FAIL_STOP else 'budget 20000')
    rows.append(dict(exp='E3_rc_adaptive', code=cname, decoder='BP+OSD',
                     rounds=rounds, p=p, trials=trials, failures=failures,
                     lfr=round(failures / trials, 6),
                     ci_lo=round(lo, 6), ci_hi=round(hi, 6),
                     seed=seeds[0], n_batches=batch_idx,
                     batch_seeds=';'.join(map(str, seeds)),
                     stop_reason=stop,
                     hx_sha256=code['hx_sha'], hz_sha256=code['hz_sha']))
    print(f"DONE {cname} p={p}: {failures}/{trials} [{lo:.5f},{hi:.5f}] "
          f"stop={stop} ({time.time()-t0:.0f}s)", flush=True)

write_csv(f'repeated_cycle_adaptive_{cname.lower()}.csv', rows)
