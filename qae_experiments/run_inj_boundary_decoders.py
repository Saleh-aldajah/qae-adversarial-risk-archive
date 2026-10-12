#!/usr/bin/env python3
"""
run_inj_boundary_decoders.py  —  cross-decoder replication of the BB72
injection boundary (Remark rem:decoder-inst, Corollary cor:workfactor).

Question: is the weight boundary at t+1 = 3 (Theorem 3) an artifact of
BP+OSD, or structural?  We replay the hardware-probe matrix (controls of
weight 0/1/2 vs O5-certified sharpness halves of weight 3) under three
decoder families:
    BP+OSD (ms 0.625, CS-7)         -- manuscript reference decoder
    Union-Find (uf_bfs)             -- matching-free graph decoder
    BP-guided MWPM (bp_guided)      -- belief-reweighted matching
in the single-round phenomenological model that mirrors the singleshot
hardware probes:  e = injected XOR Bernoulli(p)^n,  s = H e XOR
Bernoulli(p)^m,  failure iff residual e+c outside the stabiliser group.

Expected signature (pre-registered 2026-09-24): for every decoder,
max LFR over W<=2 controls ~ 0, and every certified pair (T, T') has a
systematically failing half (max(LFR_T, LFR_T') near 1); the adversarial
work factor t+1 = 3 is decoder-independent.

Output: data/injection_boundary_decoders.csv
Batch seeds: stable_seed('IBD', side, kind, idx, decoder, p, batch).

Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
import sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from bb_codes import BB72, syn_from_mask
from decoders import make_bposd, arr_to_mask, syn_array, bernoulli_mask
from uf_bfs import build_adj, uf_decode
from bp_guided import BpGuidedMwpm
from qae_utils import stable_seed, wilson95, write_csv
from run_hw_bb72_injection import (certified_halves, in_rowspace,
                                   O5_LEX_X, O5_LEX_Z, N_DATA, N_CHECKS)

P = 0.003
TRIALS_CTRL = 8_000
TRIALS_SHARP = 4_000
BATCH = 2_000

n, n2 = N_DATA, N_CHECKS
rng_probe = np.random.default_rng(stable_seed('IBD', 'probes'))


def probes_for(side):
    cols = BB72['hz_cols'] if side == 'X' else BB72['hx_cols']
    witness = O5_LEX_X if side == 'X' else O5_LEX_Z
    pairs = certified_halves(witness, cols,
                             *( (BB72['HX_rref'], BB72['HX_pivots']) if side=='X'
                                else (BB72['HZ_rref'], BB72['HZ_pivots']) ),
                             4)
    pr = [('control', 0, (), None, 0)]
    singles = rng_probe.choice(n, 6, replace=False)
    for i, q in enumerate(singles):
        pr.append(('random1', 1, (int(q),), None, i + 1))
    for i in range(6):
        ab = tuple(sorted(rng_probe.choice(n, 2, replace=False).tolist()))
        pr.append(('random2', 2, ab, None, i + 1))
    for li, (T, Tp) in enumerate(pairs):
        pr.append(('sharp3', 3, T, 'a', li))
        pr.append(('sharp3', 3, Tp, 'b', li))
    return pr


def make_decoders(side):
    H = BB72['HZ'] if side == 'X' else BB72['HX']
    return {
        'BP+OSD':  ('bposd', make_bposd(H, P)),
        'UF':      ('uf', build_adj(H, n, n2)),
        'BPguided': ('bpgm', BpGuidedMwpm(H, P)),
    }


def decode_with(tag_obj, tag, syn_int, H):
    name, obj = tag_obj
    if name == 'bposd':
        return arr_to_mask(obj.decode(syn_array(syn_int, n2)))
    if name == 'uf':
        return uf_decode(obj, syn_int, n2)
    return obj.decode_mask(syn_int)


def benign(side, resid_mask):
    v = np.array([(resid_mask >> i) & 1 for i in range(n)], dtype=np.uint8)
    if side == 'X':
        return in_rowspace(v, BB72['HX_rref'], BB72['HX_pivots'])
    return in_rowspace(v, BB72['HZ_rref'], BB72['HZ_pivots'])


rows = []
t00 = time.time()
for side in ('X', 'Z'):
    H = BB72['HZ'] if side == 'X' else BB72['HX']
    cols = BB72['hz_cols'] if side == 'X' else BB72['hx_cols']
    decs = make_decoders(side)
    for dname, dobj in decs.items():
        for kind, w, pat, partner, idx in probes_for(side):
            inj = int(sum(1 << q for q in pat))
            trials = TRIALS_SHARP if kind == 'sharp3' else TRIALS_CTRL
            fails = done = batch = 0
            while done < trials:
                seed = stable_seed('IBD', side, kind, idx, partner,
                                   dname, P, batch)
                rng = np.random.default_rng(seed)
                for _ in range(min(BATCH, trials - done)):
                    e = inj ^ bernoulli_mask(n, P, rng)
                    s = syn_from_mask(e, cols)
                    for i in range(n2):
                        if rng.random() < P:
                            s ^= (1 << i)
                    c = decode_with(dobj, dname, s, H)
                    if not benign(side, e ^ c):
                        fails += 1
                    done += 1
                batch += 1
            lo, hi = wilson95(fails, trials)
            rows.append(dict(exp='IBD', side=side, decoder=dname, kind=kind,
                             weight=w, pattern=' '.join(map(str, pat)),
                             partner=partner or '', logical_id=idx, p=P,
                             trials=trials, failures=fails,
                             lfr=round(fails / trials, 6),
                             ci_lo=round(lo, 6), ci_hi=round(hi, 6),
                             seed=stable_seed('IBD', side, kind, idx,
                                              partner, dname, P, 0),
                             hx_sha256=BB72['hx_sha'],
                             hz_sha256=BB72['hz_sha']))
            print(f"{side} {dname:8s} {kind:8s} w{w} #{idx}{partner or ''}: "
                  f"{fails}/{trials}  ({time.time()-t00:.0f}s)", flush=True)

write_csv('injection_boundary_decoders.csv', rows)
print(f"DONE injection-boundary cross-decoder study ({time.time()-t00:.0f}s)")
