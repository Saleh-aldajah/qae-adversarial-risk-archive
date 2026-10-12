#!/usr/bin/env python3
"""Rescue runner: complete the sym_simplex tasks stranded in pool.map chunk 1.
Runs as kimi; writes failbits .npy with the SAME deterministic content the
original run_grid would produce (same seeds, same decoder)."""
import os, sys, time
HERE = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, HERE)
import numpy as np
import cmp_common as C

FB = os.path.join(HERE, 'results', 'failbits')
os.makedirs(FB, exist_ok=True)

def run_one(p):
    out = os.path.join(FB, f'sym_simplex_{p}.npy')
    t0 = time.time()
    dec = C.DECODER_SPECS['sym_simplex'](p)
    ez, ex, seed = C.trial_errors(p, C.TRIALS)
    HX, HZ = C.BB72['HX'], C.BB72['HZ']
    fails = np.zeros(C.TRIALS, dtype=np.uint8)
    for t in range(C.TRIALS):
        sx = (HZ @ ex[t]) % 2; sz = (HX @ ez[t]) % 2
        px_ = dec.decode_x(sx); pz_ = dec.decode_z(sz)
        fails[t] = 1 if (dec.fail_x(ex[t], px_) or dec.fail_z(ez[t], pz_)) else 0
    k = int(fails.sum()); dt = time.time() - t0
    lo, hi = C.wilson95(k, C.TRIALS)
    np.save(out, fails)
    print(f'RESCUE sym_simplex p={p}: {k}/{C.TRIALS} [{lo:.5f},{hi:.5f}] ({dt:.0f}s)', flush=True)

if __name__ == '__main__':
    for p in [float(x) for x in sys.argv[1:]] or [0.008, 0.006]:
        run_one(p)
