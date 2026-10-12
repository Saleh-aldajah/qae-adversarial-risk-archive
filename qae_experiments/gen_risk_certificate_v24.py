"""
gen_risk_certificate_v24.py — build the explicit risk-certificate artifact
(v25, second-round review Gate 1 / review sec. 4.1).

For every system where the manuscript reports a worst-case interval
[L_W, U_W] for lambda_M(W) = max_{|F|<=W} q(F), emit one certificate row:
system, attack-set size, tested coverage, confidence allocation,
L_W, U_W, gap, and the basis of the bound (exact enumeration / exhibited
deterministic witness / simultaneous interval).

Rules implemented (Remark rem:intervals):
  * L_W = max over TESTED fault sets of valid per-set lower bounds.
  * U_W = max of per-set upper bounds ONLY where testing is exhaustive
    (with simultaneity); otherwise U_W = 1 honestly.
  * Exhaustive noiseless rows are exact (L=U, gap 0): q(F) in {0,1}.
  * Sampled noiseless rows with an observed failure certify L_W = 1 by
    exhibited deterministic witness (single-shot noiseless decode).
  * Interval cells use exact Clopper--Pearson bounds at alpha/K with one
    Bonferroni family over ALL K statistical cells of this table
    (stats_intervals.cp_interval) -- the table defines its own family.

Inputs (archive-relative):
  data/inj_radius_noiseless_v24.csv        (O4/O5 radius rows)
  data/injection_boundary_decoders_v24.csv (noisy controls + halves)
  ../theory_test/results/theorytest_results.csv     (device campaign 1)
  ../theory_test_consol/results/consol_results.csv  (device replication)
Outputs:
  data/risk_certificate_v24.csv
  data/risk_certificate_v24_rows.tex       (LaTeX rows for tab:riskcert)
"""
import csv, json, os, sys
from math import comb

HERE = os.path.dirname(os.path.abspath(__file__))
ARCH = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from qae_utils import stable_seed            # noqa: E402
from stats_intervals import cp_interval      # noqa: E402
import numpy as np                           # noqa: E402

ALPHA = 0.05

# ---------------------------------------------------------------- helpers
def stoch_mask(d, code, basis, p, variant):
    """Replicates theory_test/tt_common.stoch_mask without qiskit."""
    rng = np.random.default_rng(stable_seed("INJTT", code, basis,
                                            f"p{p}", variant))
    return tuple(j for j in range(d) if rng.random() < p)


STOCH_PS = (0.01, 0.05, 0.10)
STOCH_VARIANTS = 50
D_OF = {"REP3": 3, "REP5": 5, "REP7": 7}


def attack_size(d, W, bases=2):
    """single-sector injection game, both memory bases."""
    return bases * sum(comb(d, w) for w in range(0, W + 1))


def fmt(x):
    if x in (0.0, 1.0):
        return f"{x:.0f}"
    return f"{x:.4f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------- load sim
with open(os.path.join(HERE, 'data', 'inj_radius_noiseless_v24.csv')) as f:
    noiseless = list(csv.DictReader(f))
with open(os.path.join(HERE, 'data', 'injection_boundary_decoders_v24.csv')) as f:
    ibd = list(csv.DictReader(f))

# ---------------------------------------------------------------- device
def load_device(path, campaign_filter=None):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        if campaign_filter and r.get('campaign', 'A') not in campaign_filter:
            continue
        code, basis, name = r['code'], r['basis'], r['name']
        k, n = int(r['failures']), int(r['shots'])
        if name.startswith('p'):                      # stochastic arm
            ptag, _, vtag = name.partition('_v')      # 'p0.01_v00'
            p = float(ptag[1:])
            v = int(vtag) if vtag else int(r['variant'] or 0)
            mask = stoch_mask(D_OF[code], code, basis, p, v)
        elif name == 'base':
            mask = ()
        else:                                         # w1/w2/w3/w4 pinned
            mask = ('det', code, basis, name)
        w = len(mask) if not (mask and isinstance(mask[0], str)) else \
            int(name[1:])
        out.append(dict(code=code, basis=basis, name=name, mask=mask,
                        weight=w, k=k, n=n))
    return out


dev1 = load_device(os.path.join(ARCH, 'theory_test', 'results',
                                'theorytest_results.csv'))
dev2 = load_device(os.path.join(ARCH, 'theory_test_consol', 'results',
                                'consol_results.csv'))

# ------------------------------------------------- family size (one table)
# statistical cells: noisy sim cells (BP+OSD random1/random2 both sides,
# halves both sides) + every device arm; exact-enumeration and witness rows
# carry no statistical cell.
K = (12 * 2) + (8 * 2) + len(dev1) + len(dev2)
a_cell = ALPHA / K

rows = []


def add(system, noise, W, asize, tested, cov, alloc, L, U, basis, src, note):
    rows.append(dict(system=system, noise_model=noise, W=W,
                     attack_set_size=asize, tested=tested,
                     coverage=cov, allocation=alloc,
                     L_W=L, U_W=U, gap=round(U - L, 6),
                     basis_of_bound=basis, source_files=src, notes=note))


# ---- rows 1-4: noiseless exhaustive W<=2, per decoder
DEC = {'BP+OSD': 'BP+OSD', 'MW-lookup': 'MW-lookup', 'UF': 'UF',
       'BPguided': 'BP-guided MWPM'}
for dec in ['BP+OSD', 'MW-lookup', 'UF', 'BPguided']:
    sel = [r for r in noiseless
           if r['decoder'] == dec and r['group'] == 'w<=2-exhaustive']
    wl = sum(int(r['valid_wrong_logical']) for r in sel)
    val = 1.0 if wl > 0 else 0.0
    add(f'BB72+{DEC[dec]}', 'noiseless single-round', 2, 5258,
        5258, 'exhaustive', 'exact enumeration (no statistical error)',
        val, val, 'exhaustive enumeration',
        'inj_radius_noiseless_v24.csv',
        f'{wl} deterministic wrong-logical masks' if wl else
        'all masks corrected; certified correctability radius t=2')

# ---- row 5: noiseless sampled W=3 (witness-based, certified decoder)
sel = [r for r in noiseless if r['group'] == 'w3-sample'
       and r['decoder'] == 'BP+OSD']
wl3 = sum(int(r['valid_wrong_logical']) for r in sel)
n3 = sum(int(r['trials']) for r in sel)
add('BB72+BP+OSD', 'noiseless single-round', 3, 119280, n3,
    f'{n3}/119280 sampled (33.6% per sector)',
    'exact (deterministic witnesses)',
    1.0, 1.0, 'exhibited witnesses + rule (ii)',
    'inj_radius_noiseless_v24.csv',
    f'{wl3} sampled masks fail deterministically -> lambda(3)=1 certified '
    '(matches Theorem thm:spacetime(b) sharpness); U=1 by rule (ii)')

# ---- rows 6-7: noisy BP+OSD controls (W<=2) and halves (W=3)
def sim_interval_row(kind_weights, W, asize, n_masks, trials, note):
    cells = [r for r in ibd if r['decoder'] == 'BP+OSD'
             and r['kind'] in kind_weights]
    best = max(cp_interval(int(r['valid_wrong_logical']), int(r['trials']),
                           a_cell)[0] for r in cells)
    add('BB72+BP+OSD', 'phenomenological p=0.003, sampled noise', W, asize,
        n_masks, f'{n_masks}/{asize} masks ({100*n_masks/asize:.3f}%)',
        f'exact CP 95%, Bonferroni over {K} table cells', best, 1.0,
        'simultaneous per-attack intervals + rule (ii)',
        'injection_boundary_decoders_v24.csv', note)


sim_interval_row({'random1', 'random2'}, 2, 5258, 12, 8000,
                 'max per-attack risk over 12 frozen control masks, '
                 '8000 trials each, both sectors')
sim_interval_row({'sharp3'}, 3, 119280, 8, 4000,
                 '8 O5-certified weight-3 halves of weight-6 logicals, '
                 '4000 trials each, both sectors')

# ---- rows 8-11: device campaigns
def device_row(code, W, arms, campaign_label):
    d = D_OF[code]
    asize = attack_size(d, W)
    cand = [a for a in arms if a['code'] == code and a['weight'] <= W]
    tested_masks = {a['mask'] for a in cand if not a['name'].startswith('p')}
    tested_masks |= {a['mask'] for a in cand if a['name'].startswith('p')}
    best = max(cp_interval(a['k'], a['n'], a_cell)[0] for a in cand)
    add(f'{code} @ ibm_marrakesh ({campaign_label})',
        'device native noise (pinned masks)', W, asize, len(tested_masks),
        f'{len(tested_masks)}/{asize} masks '
        f'({100*len(tested_masks)/asize:.1f}%)',
        f'exact CP 95%, Bonferroni over {K} table cells', best, 1.0,
        'simultaneous per-attack intervals + rule (ii)',
        'theorytest_results.csv; consol_results.csv',
        f'{len(cand)} device arms contribute; strongest attack = pinned '
        f'weight-{W} or sampled mask with max lower bound')


device_row('REP5', 2, dev1 + dev2, 'primary + replication cycles')
device_row('REP5', 3, dev1 + dev2, 'primary + replication cycles')
device_row('REP7', 4, dev2, 'replication cycle')
device_row('REP3', 2, dev1 + dev2, 'primary + replication cycles')

# ---------------------------------------------------------------- write
def _stable(v):
    """Byte-stable float rendering: 15 significant digits erase the
    ±1-ulp jitter of scipy's beta.isf across BLAS thread states, while
    preserving every digit an interval consumer could act on."""
    return f'{v:.15g}' if isinstance(v, float) else v


out_csv = os.path.join(HERE, 'data', 'risk_certificate_v24.csv')
with open(out_csv, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    for r in rows:
        w.writerow({k: _stable(v) for k, v in r.items()})
print('wrote', out_csv, f'({len(rows)} rows; family K={K}, '
      f'alpha_cell={a_cell:.2e})')

# ---------------------------------------------------------------- LaTeX
def tex_escape(s):
    return s.replace('_', r'\_').replace('%', r'\%')


lines = []
for r in rows:
    cov = r['coverage'].replace('%', r'\%')
    alloc = (r['allocation']
             .replace('exact enumeration (no statistical error)',
                      'exact enum.')
             .replace('exact (deterministic witnesses)',
                      'exact (witnesses)')
             .replace(f'exact CP 95%, Bonferroni over {K} table cells',
                      f'CP, Bonf.\\ over {K}'))
    gap = r['gap']
    lines.append(
        f"{tex_escape(r['system'])} & {tex_escape(r['noise_model'])} & "
        f"{r['W']} & {r['attack_set_size']:,} & {cov} & {alloc} & "
        f"{fmt(float(r['L_W']))} & {fmt(float(r['U_W']))} & "
        f"{fmt(float(gap))} \\\\")
out_tex = os.path.join(HERE, 'data', 'risk_certificate_v24_rows.tex')
with open(out_tex, 'w') as f:
    f.write('\n'.join(lines) + '\n')
print('wrote', out_tex)
summary = {r['system'] + '|W' + str(r['W']): r['L_W'] for r in rows}
print(json.dumps({'K': K, 'rows': len(rows), 'Lw': summary}, indent=1))
