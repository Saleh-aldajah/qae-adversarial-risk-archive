#!/usr/bin/env python3
"""comparator_timing.py — clean single-process decode-time probe.
Measures wall time on a probe slice of the SAME pinned error instances,
then extrapolates to the full 2*TRIALS sector-decodes for comparability
with run_grid's 'sec' column. Output: results/comparator_timing.csv"""
import os, sys, time, csv
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cmp_common as C

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'results', 'comparator_timing.csv')
PROBE = {'bposd': 2000, 'relay': 2000, 'sym_bare': 2000,
         'sym_simplex': 100, 'sym_pre_simplex': 100,
         'sym_bp_simplex': 200, 'sym_bp_pre_simplex': 200}

rows = []
for key in C.DECODER_SPECS:
    n_probe = PROBE.get(key, 500)
    for p in C.PS_STD:
        dec = C.DECODER_SPECS[key](p)
        ez, ex, seed = C.trial_errors(p, C.TRIALS)
        HX, HZ = C.BB72['HX'], C.BB72['HZ']
        t0 = time.time()
        for t in range(n_probe):
            sx = (HZ @ ex[t]) % 2; sz = (HX @ ez[t]) % 2
            dec.decode_x(sx); dec.decode_z(sz)
        dt = time.time() - t0
        sec_est = dt / n_probe * C.TRIALS
        rows.append(dict(decoder_key=key, p=p, n_probe=n_probe,
                         probe_sec=round(dt, 2), sec_est=round(sec_est, 2)))
        print(f'{key:22s} p={p:.3f}: {dt:.1f}s/{n_probe} -> est {sec_est:.0f}s/task', flush=True)
with open(OUT, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print('wrote', OUT)
