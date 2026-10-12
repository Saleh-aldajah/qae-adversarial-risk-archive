#!/usr/bin/env python3
"""assemble_grid.py — reconstruct comparator_grid.csv from failbits .npy files.
Used because the original pool.map run was interrupted (chunk-1 tail) and its
in-memory rows were lost; every CSV field except per-task wall time ('sec') is
deterministically recoverable: failures/ler/CI from the failbits, seed from
stable_seed, hashes from cmp_common. 'sec' is merged from
results/comparator_timing.csv when present (clean single-process probe)."""
import os, sys, csv, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cmp_common as C

HERE = os.path.dirname(os.path.abspath(__file__))
FB  = os.path.join(HERE, 'results', 'failbits')
OUT = os.path.join(HERE, 'results', 'comparator_grid_final.csv')

NAME = {}
for key in C.DECODER_SPECS:
    try:
        NAME[key] = C.DECODER_SPECS[key](0.004).name
    except Exception as e:
        NAME[key] = key

# optional timing merge
timing = {}
tp = os.path.join(HERE, 'results', 'comparator_timing.csv')
if os.path.exists(tp):
    with open(tp) as f:
        for r in csv.DictReader(f):
            timing[(r['decoder_key'], float(r['p']))] = float(r['sec_est'])

rows = []
missing = []
for key in C.DECODER_SPECS:
    for p in C.PS_STD:
        fn = os.path.join(FB, f'{key}_{p}.npy')
        if not os.path.exists(fn):
            missing.append((key, p)); continue
        fails = np.load(fn)
        k = int(fails.sum()); n = int(fails.size)
        lo, hi = C.wilson95(k, n)
        rows.append(dict(exp='comparator_grid', code='BB72',
                         decoder=NAME[key], decoder_key=key, rounds=1, p=p,
                         trials=n, failures=k, ler=round(k/n, 6),
                         ci_lo=round(lo, 6), ci_hi=round(hi, 6),
                         seed=C.stable_seed('COMPARE', 'BB72', p),
                         stream='COMPARE',
                         sec=timing.get((key, p), float('nan')),
                         hx_sha256=C.BB72['hx_sha'], hz_sha256=C.BB72['hz_sha'],
                         assembled='failbits'))
print('missing tasks:', missing)
if missing and '--allow-incomplete' not in sys.argv:
    sys.exit(2)
rows.sort(key=lambda r: (list(C.DECODER_SPECS).index(r['decoder_key']), r['p']))
with open(OUT, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    for r in rows: w.writerow(r)
print(f'wrote {OUT}: {len(rows)} rows')
