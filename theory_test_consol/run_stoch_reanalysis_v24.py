#!/usr/bin/env python3
"""
run_stoch_reanalysis_v24.py — mask-conditioned reanalysis of the stochastic
injection arms (review finding C03 and Sec. 6.1-6.3; supersedes the v23
"naive bound falsified" verdicts).

Defect repaired: the v23 decision rule compared pooled stochastic-arm LFR
against  d0_hi + BinomialTail(d,t,p) + TOL_STOCH,  a threshold valid only
for FRESHLY resampled masks.  Both campaigns injected 50 PINNED masks per
cell (seed formula stable_seed('INJTT', code, basis, p, variant)), so the
estimand is the mask-mixture mean over those 50 fixed masks and the
correct naive threshold conditions on the REALISED mask weights:

    cond_naive = d0_hi + (1/50) * #variants with w(mask) >= t+1 + TOL_STOCH

For completeness the mask-conditioned composed tail (Binomial weight x
Poisson(lambda_N) native faults, lambda_N from the pinned consolidation
analysis) is also reported where lambda_N is available.

Outputs:
  results/stoch_reanalysis_v24.csv   (all cells, all bound variants)
  results/stoch_reanalysis_v24.json  (summary + chronology statement)

Offline: reads only archived CSV/JSON; no hardware access, no qiskit.
"""
import csv, json, math, hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
TT = HERE.parent / 'theory_test'
RES_C1 = TT / 'results' / 'theorytest_results.csv'
RES_A = HERE / 'results' / 'consol_results.csv'
VERDICT_A = HERE / 'results' / 'consol_verdict.json'

ROUNDS = 4
STOCH_PS = (0.01, 0.05, 0.10)
STOCH_VARIANTS = 50
TOL_STOCH = 0.002
D, T = 5, 2          # stochastic arms exist only for REP5


def stable_seed(*args):
    key = "|".join(str(a) for a in args).encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:4], 'big')


def stoch_mask(code, basis, p, variant):
    import numpy as np
    rng = np.random.default_rng(stable_seed("INJTT", code, basis, f"p{p}", variant))
    return [j for j in range(D_OF[code]) if rng.random() < p]


def binom_tail(d, t, p):
    return sum(math.comb(d, k) * p**k * (1 - p)**(d - k)
               for k in range(t + 1, d + 1))


def poisson_tail(lam, k):
    return 1.0 - sum(math.exp(-lam) * lam**j / math.factorial(j)
                     for j in range(max(k, 0)))


def wilson95(k, n):
    if n == 0:
        return (0.0, 1.0)
    z = 1.959963984540054
    ph = k / n
    den = 1 + z * z / n
    cen = ph + z * z / (2 * n)
    rad = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))
    return ((cen - rad) / den, (cen + rad) / den)


D_OF = {'REP5': 5}

MASKS = {(basis, p, v): stoch_mask('REP5', basis, p, v)
         for basis in ('X', 'Z') for p in STOCH_PS
         for v in range(STOCH_VARIANTS)}

LAMBDA_A_REP5 = json.load(open(VERDICT_A))['lambda_N']['A']['REP5']


def load_cells(path, campaign_key=None):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    cells = {}
    for basis in ('X', 'Z'):
        base = [r for r in rows if r['kind'] == 'det' and r['name'] == 'base'
                and r['basis'] == basis and r['code'] == 'REP5'
                and (campaign_key is None or r.get('campaign') == campaign_key)]
        assert len(base) == 1, f'base arm not unique for {basis}: {len(base)}'
        d0_hi = float(base[0]['ci_hi'])
        for p in STOCH_PS:
            pool = [r for r in rows if r['kind'] == 'stoch'
                    and r['basis'] == basis and r['code'] == 'REP5'
                    and abs(float(r.get('p') or -1) - p) < 1e-9
                    and (campaign_key is None or r.get('campaign') == campaign_key)]
            fails = sum(int(r['failures']) for r in pool)
            shots = sum(int(r['shots']) for r in pool)
            cells[(basis, p)] = dict(fails=fails, shots=shots, d0_hi=d0_hi,
                                     n_variants=len(pool))
    return cells


rows = []
for src, path, camp, lam in (('campaign1_20260828', RES_C1, None, None),
                             ('consolidationA_20260906', RES_A, 'A',
                              LAMBDA_A_REP5)):
    cells = load_cells(path, camp)
    for (basis, p), cell in sorted(cells.items()):
        fails, shots, d0_hi = cell['fails'], cell['shots'], cell['d0_hi']
        ler = fails / shots
        lo, hi = wilson95(fails, shots)
        weights = [len(MASKS[(basis, p, v)]) for v in range(STOCH_VARIANTS)]
        realized_tail = sum(1 for w in weights if w >= T + 1) / STOCH_VARIANTS
        naive23 = d0_hi + binom_tail(D, T, p) + TOL_STOCH
        cond_naive = d0_hi + realized_tail + TOL_STOCH
        comp23 = comp_cond = None
        if lam is not None:
            comp23 = d0_hi + sum(
                math.comb(D, k) * p**k * (1 - p)**(D - k) *
                poisson_tail(lam, T + 1 - k) for k in range(D + 1)) + TOL_STOCH
            comp_cond = d0_hi + sum(
                poisson_tail(lam, T + 1 - w) for w in weights
            ) / STOCH_VARIANTS + TOL_STOCH
        rows.append(dict(
            exp='stoch_reanalysis_v24', source=src, code='REP5', basis=basis,
            p=p, variants=cell['n_variants'], shots=shots, failures=fails,
            ler=round(ler, 6), ci_lo=round(lo, 6), ci_hi=round(hi, 6),
            d0_hi=d0_hi,
            realized_mask_tail_ge3=realized_tail,
            binom_tail_model=round(binom_tail(D, T, p), 6),
            naive23_bound=round(naive23, 6),
            mask_conditioned_naive_bound=round(cond_naive, 6),
            composed23_bound=(round(comp23, 6) if comp23 is not None else ''),
            mask_conditioned_composed_bound=(round(comp_cond, 6)
                                             if comp_cond is not None else ''),
            lambda_N=(lam if lam is not None else ''),
            exceeds_naive23=int(ler > naive23),
            exceeds_mask_conditioned=int(ler > cond_naive),
            margin_to_conditioned=round(cond_naive - ler, 6),
        ))
        print(f"{src} {basis} p={p}: LFR={ler:.4f} "
              f"naive23={naive23:.4f} cond={cond_naive:.4f} "
              f"exceeds_cond={ler > cond_naive}")

out_csv = HERE / 'results' / 'stoch_reanalysis_v24.csv'
with open(out_csv, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

any_exceed = any(r['exceeds_mask_conditioned'] for r in rows)
summary = dict(
    conclusion=('No stochastic cell exceeds the mask-conditioned naive '
                'threshold; the v23 "naive bound falsified" verdict is NOT '
                'SUPPORTED under the correct fixed-mask estimand and is '
                'withdrawn. The Binomial x Poisson composed model is '
                'relabelled as a discovery motivated by campaign-1 '
                'deviations, not a prespecified prediction.'
                if not any_exceed else
                'AT LEAST ONE CELL EXCEEDS THE CONDITIONED THRESHOLD'),
    any_cell_exceeds_conditioned=bool(any_exceed),
    cells=len(rows))
with open(HERE / 'results' / 'stoch_reanalysis_v24.json', 'w') as f:
    json.dump(summary, f, indent=1)
print('Saved', out_csv.name, f'({len(rows)} rows)')
print('CONCLUSION:', summary['conclusion'][:140])
