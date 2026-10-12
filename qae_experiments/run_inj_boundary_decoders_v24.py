#!/usr/bin/env python3
"""
run_inj_boundary_decoders_v24.py — rebuilt cross-decoder injection study
(review Sec. 5.3 and findings C03/C07; supersedes run_inj_boundary_decoders.py).

Protocol repairs relative to the v23 study:
  * The probe set is generated ONCE from a single frozen seed and replayed
    identically to every decoder (v23 regenerated probes per decoder).
  * Native errors and measurement-flip realisations are sampled ONCE per
    (side, probe, trial) into a frozen table, then decoded by every decoder
    on IDENTICAL inputs (v23 drew decoder-dependent random streams, so the
    decoders never saw the same errors).
  * The noiseless radius test (Phase A) is separated from the noisy
    injection experiment (Phase B): no syndrome-bit noise contaminates the
    radius claims (v23 mixed Bernoulli(p) syndrome flips into both).
  * Endpoint is the four-category classification (finding C07), with
    validity tested on the TRUE residual syndrome (second-round review
    sec. 4.2; regression tests T1--T4 run at every launch):
      valid_correct        -- residual syndrome-zero, benign (stabilizer)
      valid_wrong_logical  -- residual syndrome-zero, nontrivial
                              logical residual (decoder logical failure)
      invalid_residual     -- residual has nonzero TRUE syndrome (the
                              correction does not restore the code space;
                              NOT a code failure)
      abort                -- decoder raised / no answer
  * Availability is reported alongside: restoration_failure =
    1 - valid_correct/trials per (decoder, probe), so that an
    always-aborting decoder scores restoration failure 1, not 0.
  * A minimum-weight lookup reference, complete by construction over all
    weight<=3 errors (enumeration matches the archived O2/O3 certificate),
    is included as the radius-complete reference decoder (review Sec. 11.3).

Phase A (noiseless radius): exhaustive weights 0..2 (2,629 masks per side),
plus a frozen uniform sample of weight-3 masks and the 8 O5-certified
sharpness halves.  Phase B (noisy phenomenological injection): frozen probe
matrix (control, 6 random weight-1, 6 random weight-2, 8 certified halves)
x frozen native-error table, decoded by BP+OSD, UF-BFS, BP-guided MWPM and
the MW-lookup reference; paired contrasts use exact McNemar tests.

Outputs:
  data/inj_radius_noiseless_v24.csv           (Phase A, per-decoder summaries)
  data/injection_boundary_decoders_v24.csv    (Phase B, per-probe summaries)
  data/injection_boundary_mcnemar_v24.csv     (Phase B, paired contrasts)
  data/ibd_v24_trial_categories.npz           (per-trial category codes)
  data/ibd_v24_freeze.json                    (frozen seeds + probe table)
"""
import sys, os, time, json, itertools
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
W3_SAMPLE = 20_000
CATS = ['valid_correct', 'valid_wrong_logical', 'invalid_residual', 'abort']

n, n2 = N_DATA, N_CHECKS
t00 = time.time()

# ---------------- frozen probe set (generated once, decoder-independent) ----
rng_probe = np.random.default_rng(stable_seed('IBDv24', 'probes'))


def probes_for(side):
    cols = BB72['hz_cols'] if side == 'X' else BB72['hx_cols']
    witness = O5_LEX_X if side == 'X' else O5_LEX_Z
    pairs = certified_halves(witness, cols,
                             *((BB72['HX_rref'], BB72['HX_pivots']) if side == 'X'
                               else (BB72['HZ_rref'], BB72['HZ_pivots'])), 4)
    pr = [('control', 0, (), None, 0)]
    for i, q in enumerate(rng_probe.choice(n, 6, replace=False)):
        pr.append(('random1', 1, (int(q),), None, i + 1))
    for i in range(6):
        ab = tuple(sorted(rng_probe.choice(n, 2, replace=False).tolist()))
        pr.append(('random2', 2, ab, None, i + 1))
    for li, (T, Tp) in enumerate(pairs):
        pr.append(('sharp3', 3, tuple(sorted(T)), 'a', li))
        pr.append(('sharp3', 3, tuple(sorted(Tp)), 'b', li))
    return pr


PROBES = {side: probes_for(side) for side in ('X', 'Z')}

# ---------------- frozen native-error table (Phase B) -----------------------
freeze = {'probe_seed': int(stable_seed('IBDv24', 'probes')),
          'trial_seed': int(stable_seed('IBDv24', 'trials')),
          'p': P, 'trials_ctrl': TRIALS_CTRL, 'trials_sharp': TRIALS_SHARP,
          'probes': {s: [(k, w, list(p_), pt or '', i)
                         for (k, w, p_, pt, i) in PROBES[s]] for s in ('X', 'Z')}}

rng_trials = np.random.default_rng(stable_seed('IBDv24', 'trials'))
TRIAL_TABLE = {}   # (side, probe_idx) -> (eb uint8 (T,72), mb uint8 (T,36))
for side in ('X', 'Z'):
    for pi, (kind, w, pat, partner, idx) in enumerate(PROBES[side]):
        T = TRIALS_SHARP if kind == 'sharp3' else TRIALS_CTRL
        eb = (rng_trials.random((T, n)) < P).astype(np.uint8)
        mb = (rng_trials.random((T, n2)) < P).astype(np.uint8)
        TRIAL_TABLE[(side, pi)] = (eb, mb)


def bits_to_int(row):
    return int.from_bytes(np.packbits(row, bitorder='little').tobytes(),
                          'little')

# ---------------- decoders ---------------------------------------------------

def make_decoders(side):
    H = BB72['HZ'] if side == 'X' else BB72['HX']
    return {'BP+OSD': ('bposd', make_bposd(H, P)),
            'UF': ('uf', build_adj(H, n, n2)),
            'BPguided': ('bpgm', BpGuidedMwpm(H, P))}


def decode_with(tag_obj, syn_int):
    name, obj = tag_obj
    if name == 'bposd':
        return arr_to_mask(obj.decode(syn_array(syn_int, n2)))
    if name == 'uf':
        return uf_decode(obj, syn_int, n2)
    return obj.decode_mask(syn_int)


def stab_rowspace(side):
    return ((BB72['HX_rref'], BB72['HX_pivots']) if side == 'X'
            else (BB72['HZ_rref'], BB72['HZ_pivots']))


def categorize(side, Hcols, inj, e_n, m, c_hat):
    """Four-category endpoint (C07), classified by the TRUE residual.

    Simulation knows the sampled faults (e_n) and measurement flips (m),
    so validity is tested on the true residual r = c_hat ^ e_n ^ inj:
      invalid_residual := r has nonzero TRUE syndrome (the correction
      does not restore the code space);  valid trials are then split by
      whether r is a stabilizer (benign) or a nontrivial logical.

    v24 defect (second-round review sec. 4.2): validity was tested
    against the OBSERVED syndrome s = syn(e_n ^ inj) ^ m. With m != 0 a
    correction matching s leaves true residual syndrome m != 0 and was
    mislabeled --- counterexample e=0, c_hat=single fault, m=syndrome(c):
    old rule returned valid_wrong_logical for a correction that never
    restored the code space. The m argument is now unused (decoding
    already consumed it); it is kept for a stable signature.
    """
    if c_hat is None:
        return 3  # abort
    resid = c_hat ^ e_n ^ inj
    if syn_from_mask(resid, Hcols) != 0:
        return 2  # invalid_residual: true residual syndrome nonzero
    v = np.array([(resid >> i) & 1 for i in range(n)], np.uint8)
    rref, piv = stab_rowspace(side)
    return 0 if in_rowspace(v, rref, piv) else 1


def endpoint_regression_tests():
    """Second-round-review counterexamples, run before every campaign.

    (T1) e=0, inj=0, c_hat=single fault, m=syndrome(c_hat): observed
         syndrome equals syn(c_hat), so the observed-syndrome rule would
         call the trial valid and the residual logical; the true
         residual c_hat has nonzero syndrome -> invalid_residual.
    (T2) e=c_hat_fault, m=syndrome(e), c_hat=0: observed syndrome is 0;
         the true residual e has nonzero syndrome -> invalid_residual.
    (T3) clean trial -> valid_correct.
    (T4) noiseless half-vs-half of a certified weight-6 logical:
         residual = full logical -> valid_wrong_logical.
    """
    side = 'X'
    cols = BB72['hz_cols']
    q = 5
    c = 1 << q
    m = syn_from_mask(c, cols)
    assert categorize(side, cols, 0, 0, m, c) == 2, \
        'T1: review sec. 4.2 counterexample mislabeled'
    assert categorize(side, cols, 0, c, m, 0) == 2, \
        'T2: true-residual syndrome check failed'
    assert categorize(side, cols, 0, 0, 0, 0) == 0, 'T3: clean trial'
    sharp = {}
    for kind, w, pat, tag, idx in PROBES[side]:
        if kind == 'sharp3':
            sharp.setdefault(idx, {})[tag] = pat
    idx0 = sorted(sharp)[0]
    half = int(sum(1 << x for x in sharp[idx0]['a']))
    rest = int(sum(1 << x for x in sharp[idx0]['b']))
    assert categorize(side, cols, rest, 0, 0, half) == 1, \
        'T4: certified logical residual must be wrong-logical'
    print('endpoint regression tests OK (T1-T4)', flush=True)


def mw_lookup_reference(side):
    """Minimum-weight lookup decoder, complete over weight<=3 by enumeration."""
    cols = BB72['hz_cols'] if side == 'X' else BB72['hx_cols']
    table = {0: 0}
    for w in (1, 2, 3):
        for comb in itertools.combinations(range(n), w):
            mask = 0
            for q in comb:
                mask |= 1 << q
            s = syn_from_mask(mask, cols)
            if s not in table:      # first seen at lowest weight, deterministic
                table[s] = mask
    return table


# ---------------- Phase A: noiseless radius test -----------------------------
endpoint_regression_tests()
if os.environ.get('IBD_TEST_ONLY') == '1':
    sys.exit(0)
rows_a = []
for side in ('X', 'Z'):
    cols = BB72['hz_cols'] if side == 'X' else BB72['hx_cols']
    decs = make_decoders(side)
    lut = mw_lookup_reference(side)
    # exhaustive weights 0..2
    masks02 = [0] + [1 << q for q in range(n)]
    masks02 += [(1 << a) | (1 << b) for a, b in itertools.combinations(range(n), 2)]
    # frozen weight-3 sample + certified halves
    rng3 = np.random.default_rng(stable_seed('IBDv24', 'w3', side))
    seen = set()
    w3 = []
    while len(w3) < W3_SAMPLE:
        comb = tuple(sorted(rng3.choice(n, 3, replace=False).tolist()))
        if comb in seen:
            continue
        seen.add(comb)
        w3.append(sum(1 << q for q in comb))
    for kind, w, pat, partner, idx in PROBES[side]:
        if kind == 'sharp3':
            w3.append(sum(1 << q for q in pat))
    for group, masks in (('w<=2-exhaustive', masks02), ('w3-sample', w3)):
        counts = {d: np.zeros(4, np.int64) for d in list(decs) + ['MW-lookup']}
        for e in masks:
            s = syn_from_mask(int(e), cols)
            for dname, dobj in decs.items():
                try:
                    c = decode_with(dobj, s)
                except Exception:
                    c = None
                counts[dname][categorize(side, cols, int(e), 0, 0, c)] += 1
            c_lut = lut.get(s)
            counts['MW-lookup'][categorize(side, cols, int(e), 0, 0, c_lut)] += 1
        for dname, cc in counts.items():
            T = int(cc.sum())
            lo, hi = wilson95(int(cc[1]), T)
            rf = T - int(cc[0])
            rlo, rhi = wilson95(rf, T)
            rows_a.append(dict(exp='IBD-radius-v24', side=side, decoder=dname,
                               group=group, trials=T,
                               valid_correct=int(cc[0]),
                               valid_wrong_logical=int(cc[1]),
                               invalid_residual=int(cc[2]), abort=int(cc[3]),
                               lfr=round(cc[1] / T, 6), ci_lo=round(lo, 6),
                               ci_hi=round(hi, 6),
                               restoration_failure=rf,
                               rf_rate=round(rf / T, 6),
                               rf_ci_lo=round(rlo, 6), rf_ci_hi=round(rhi, 6),
                               hx_sha256=BB72['hx_sha'], hz_sha256=BB72['hz_sha']))
        print(f"A {side} {group}: " + ', '.join(
            f"{d} wl={counts[d][1]}/{len(masks)}" for d in counts),
            f"({time.time()-t00:.0f}s)", flush=True)
write_csv('inj_radius_noiseless_v24.csv', rows_a)

# ---------------- Phase B: frozen noisy injection ----------------------------
rows_b, rows_mc = [], []
trial_cat = {}
for side in ('X', 'Z'):
    cols = BB72['hz_cols'] if side == 'X' else BB72['hx_cols']
    decs = make_decoders(side)
    lut = mw_lookup_reference(side)
    all_dec = list(decs.items()) + [('MW-lookup', ('lut', lut))]
    for pi, (kind, w, pat, partner, idx) in enumerate(PROBES[side]):
        inj = int(sum(1 << q for q in pat))
        eb, mb = TRIAL_TABLE[(side, pi)]
        T = len(eb)
        cats = np.zeros((len(all_dec), T), np.uint8)
        for di, (dname, dobj) in enumerate(all_dec):
            for ti in range(T):
                e_n, m = bits_to_int(eb[ti]), bits_to_int(mb[ti])
                s = syn_from_mask(e_n ^ inj, cols) ^ m
                try:
                    c = (lut.get(s) if dobj[0] == 'lut'
                         else decode_with(dobj, s))
                except Exception:
                    c = None
                cats[di, ti] = categorize(side, cols, inj, e_n, m, c)
        trial_cat[f'{side}_{pi}'] = cats
        for di, (dname, _) in enumerate(all_dec):
            cc = np.bincount(cats[di], minlength=4)
            lo, hi = wilson95(int(cc[1]), T)
            rf = T - int(cc[0])
            rlo, rhi = wilson95(rf, T)
            rows_b.append(dict(exp='IBD-v24', side=side, decoder=dname,
                               kind=kind, weight=w,
                               pattern=' '.join(map(str, pat)),
                               partner=partner or '', logical_id=idx, p=P,
                               trials=T, valid_correct=int(cc[0]),
                               valid_wrong_logical=int(cc[1]),
                               invalid_residual=int(cc[2]), abort=int(cc[3]),
                               lfr=round(cc[1] / T, 6), ci_lo=round(lo, 6),
                               ci_hi=round(hi, 6),
                               restoration_failure=rf,
                               rf_rate=round(rf / T, 6),
                               rf_ci_lo=round(rlo, 6), rf_ci_hi=round(rhi, 6),
                               seed=freeze['trial_seed'],
                               hx_sha256=BB72['hx_sha'], hz_sha256=BB72['hz_sha']))
        # paired contrasts vs BP+OSD on valid_wrong_logical and on any failure
        ref = cats[0]
        for di, (dname, _) in enumerate(all_dec[1:], start=1):
            for ep, code in (('wrong_logical', 1), ('any_failure', None)):
                a = (cats[0] == 1) if code == 1 else (cats[0] != 0)
                b = (cats[di] == 1) if code == 1 else (cats[di] != 0)
                b10 = int(np.sum(a & ~b)); b01 = int(np.sum(~a & b))
                from scipy.stats import binomtest
                pv = float(binomtest(min(b10, b01), b10 + b01, 0.5).pvalue) \
                    if b10 + b01 else 1.0
                rows_mc.append(dict(exp='IBD-v24-mcnemar', side=side,
                                    decoder=dname, ref='BP+OSD', endpoint=ep,
                                    kind=kind, logical_id=idx,
                                    partner=partner or '', trials=T,
                                    discordant_ref_only=b10,
                                    discordant_dec_only=b01,
                                    mcnemar_p_two_sided=round(pv, 6)))
        print(f"B {side} probe#{pi} {kind} done ({time.time()-t00:.0f}s)",
              flush=True)

write_csv('injection_boundary_decoders_v24.csv', rows_b)
write_csv('injection_boundary_mcnemar_v24.csv', rows_mc)
np.savez_compressed(ROOT / 'data' / 'ibd_v24_trial_categories.npz',
                    **trial_cat)
with open(ROOT / 'data' / 'ibd_v24_freeze.json', 'w') as f:
    json.dump(freeze, f, indent=1)
print(f"DONE IBD-v24 ({time.time()-t00:.0f}s)")
