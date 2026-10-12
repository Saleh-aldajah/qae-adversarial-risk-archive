#!/usr/bin/env python3
"""
run_rc_only_v24.py  —  Repeated-cycle BP+OSD, PRIOR-ALIGNED revision
(review Sec. 5.4; supersedes run_rc_only.py for all distance-ladder uses).

Defect repaired: the v23 spacetime check matrix contained columns (with
prior p) for final-round data and measurement fault variables that the
generative sampler never produces (the final round is perfect by
construction: errors only in rounds 0..R-2).  The v24 model removes those
variables exactly:

  * data-fault variables: rounds 0..R-2  -> (R-1)*n columns; variable (r,j)
    triggers detector block r on the support of the corresponding column of
    HX (He_z) / HZ (He_x);
  * measurement-fault variables: rounds 0..R-2 -> (R-1)*n2 columns; variable
    (r,c) triggers detectors (r,c) and (r+1,c);
  * every decoded variable has prior exactly p (the sampler's rate) -- no
    variable with a nonzero prior is unsampleable, and vice versa.

The detector vector is unchanged: dtz[r] = sz_r XOR sz_{r-1}, r = 0..R-1.

Reproduces (v24):
  data/repeated_cycle_bposd_v24.csv        (14 rows, BB72+BB144, 2,000 trials)
  data/repeated_cycle_bb288_bposd_v24.csv  (7 rows, BB288, 500 trials)
  data/repeated_cycle_all_codes_v24.csv    (21 rows merged)
"""
import sys, csv, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "data"; OUT.mkdir(exist_ok=True)

from bb_codes import BB72, BB144, BB288, syn_from_mask
from decoders import BpOsdDecoder, logical_fail, arr_to_mask, bernoulli_mask
from qae_utils import stable_seed, wilson95

PS = [0.001, 0.002, 0.004, 0.006, 0.008, 0.010, 0.012]
MODEL_REV = 'v24-aligned-priors'


def spacetime_matrices(code, rounds):
    """Aligned spacetime check matrices for the perfect-final-round model."""
    n, n2 = code['n'], code['n'] // 2
    R = rounds
    ndata, nmeas = (R - 1) * n, (R - 1) * n2
    rows = R * n2
    Hm = np.zeros((rows, nmeas), dtype=np.uint8)
    for r in range(R - 1):
        for c2 in range(n2):
            Hm[r * n2 + c2, r * n2 + c2] = 1
            Hm[(r + 1) * n2 + c2, r * n2 + c2] = 1
    Dz = np.zeros((rows, ndata), dtype=np.uint8)
    Dx = np.zeros((rows, ndata), dtype=np.uint8)
    for r in range(R - 1):
        Dz[r * n2:(r + 1) * n2, r * n:(r + 1) * n] = code['HX']
        Dx[r * n2:(r + 1) * n2, r * n:(r + 1) * n] = code['HZ']
    return np.hstack([Dz, Hm]), np.hstack([Dx, Hm])


def run_rc(code, cname, rounds, ps, trials):
    n, n2 = code['n'], code['n'] // 2
    rows = []; print(f"\n{cname}  (d={rounds} rounds, {trials} trials, {MODEL_REV})")
    He_z, He_x = spacetime_matrices(code, rounds)
    for p in ps:
        seed = stable_seed('RCv24', cname, p, rounds)
        rng = np.random.default_rng(seed); failures = 0; t0 = time.time()
        cp = np.array([p] * ((rounds - 1) * n + (rounds - 1) * n2))
        dz = BpOsdDecoder(He_z, error_rate=p, channel_probs=cp, bp_method='ms',
                          ms_scaling_factor=0.625, osd_method='osd_cs',
                          osd_order=7, max_iter=100)
        dx = BpOsdDecoder(He_x, error_rate=p, channel_probs=cp, bp_method='ms',
                          ms_scaling_factor=0.625, osd_method='osd_cs',
                          osd_order=7, max_iter=100)
        for _ in range(trials):
            cum_z = cum_x = 0; szs = []; sxs = []
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
            for r in range(rounds - 1):
                for j in range(n):
                    cz[j] ^= raw_z[r * n + j]; cx[j] ^= raw_x[r * n + j]
            if logical_fail(cum_z ^ arr_to_mask(cz), cum_x ^ arr_to_mask(cx), code):
                failures += 1
        lo, hi = wilson95(failures, trials)
        rows.append(dict(exp='repeated_cycle_v24', code=cname, decoder='BP+OSD',
                         rounds=rounds, p=p, trials=trials, failures=failures,
                         lfr=round(failures / trials, 6),
                         ci_lo=round(lo, 6), ci_hi=round(hi, 6), seed=seed,
                         model_rev=MODEL_REV,
                         hx_sha256=code['hx_sha'], hz_sha256=code['hz_sha']))
        print(f"  p={p:.3f}: {failures:4d}/{trials} [{lo:.5f},{hi:.5f}]  ({time.time()-t0:.0f}s)", flush=True)
    return rows


def main():
    rows_72_144 = run_rc(BB72, 'BB72', 6, PS, 2000) + run_rc(BB144, 'BB144', 12, PS, 2000)
    rows_288 = run_rc(BB288, 'BB288', 18, PS, 500)
    rows_all = rows_72_144 + rows_288

    for fname, rows in [
        ('repeated_cycle_bposd_v24.csv', rows_72_144),
        ('repeated_cycle_bb288_bposd_v24.csv', rows_288),
        ('repeated_cycle_all_codes_v24.csv', rows_all),
    ]:
        with open(OUT / fname, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
        print(f"Saved {fname}  ({len(rows)} rows)")


if __name__ == '__main__':
    main()
