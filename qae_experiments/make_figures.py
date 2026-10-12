"""
make_figures.py  —  Regenerate all v17 manuscript figures (F1-F7).

Output: figures/F*.pdf (vector) + figures/F*.png (preview, 200 dpi)
Style: colorblind-safe low-saturation palette; 3.5in column width;
       >=8pt fonts; labeled axes; Wilson CI whiskers; open down-triangles
       for zero-failure rows (plotted at the one-sided 95% upper bound).

Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
import csv, math, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
FIG = ROOT / 'figures'; FIG.mkdir(exist_ok=True)
DATA = ROOT / 'data'
sys.path.insert(0, str(ROOT))
from qae_utils import wilson_one_sided_upper

plt.rcParams.update({
    'font.size': 8, 'axes.titlesize': 8, 'axes.labelsize': 8,
    'xtick.labelsize': 7, 'ytick.labelsize': 7, 'legend.fontsize': 6.5,
    'axes.linewidth': 0.6, 'lines.linewidth': 1.1, 'lines.markersize': 4,
    'xtick.major.width': 0.6, 'ytick.major.width': 0.6,
    'figure.dpi': 200, 'savefig.bbox': 'tight', 'pdf.fonttype': 42,
})

# Colorblind-safe low-saturation palette (muted Okabe-Ito)
C = {'bposd':   '#4C72B0',  # muted blue
     'mwpm':    '#C44E52',  # muted red
     'uf':      '#55A868',  # muted green
     'bpgm':    '#8172B3',  # muted purple
     'lookup':  '#8C8C8C',  # gray
     'pheno':   '#4C72B0',
     'cz':      '#C44E52',
     'ms':      '#55A868',
     'e1':      '#4C72B0'}

def read_csv(name):
    with open(DATA / name, newline='') as f:
        return list(csv.DictReader(f))

def save(fig, name):
    fig.savefig(FIG / f'{name}.pdf')
    fig.savefig(FIG / f'{name}.png')
    plt.close(fig)
    print(f"saved figures/{name}.pdf/.png")

def plot_series(ax, ps, lfrs, los, his, color, label, marker='o'):
    """Plot LFR curve; zero-failure rows -> open down-triangle at upper."""
    ps = np.array(ps, float)
    yerr_lo, yerr_hi, y, pxs = [], [], [], []
    zero_p, zero_hi = [], []
    for p, l, lo, hi in zip(ps, lfrs, los, his):
        if l > 0:
            pxs.append(p); y.append(l)
            yerr_lo.append(l - lo); yerr_hi.append(hi - l)
        else:
            zero_p.append(p); zero_hi.append(hi)
    if pxs:
        ax.errorbar(pxs, y, yerr=[yerr_lo, yerr_hi], color=color, marker=marker,
                    label=label, capsize=2, elinewidth=0.7, markeredgewidth=0.8)
    if zero_p:
        ax.plot(zero_p, zero_hi, linestyle='none', marker='v', mfc='none',
                mec=color, mew=0.9, label=f'{label} (0 fails, upper)')

# ── F1: minimax lower bound ──────────────────────────────────────────────
rows = read_csv('minimax_lower_bounds.csv')
p = [float(r['p_attack']) for r in rows]
lb = [float(r['lower_bound']) for r in rows]
fig, ax = plt.subplots(figsize=(3.5, 2.4))
ax.plot(p[1:], lb[1:], color=C['bposd'], marker='o', markersize=3,
        label='minimax lower bound')
ax.set_xlabel('attack probability $p_{\\mathrm{attack}}$')
ax.set_ylabel('fidelity lower bound')
ax.set_xscale('log')
ax.set_ylim(0, 1.02)
ax.grid(alpha=0.25, linewidth=0.4)
ax.legend(frameon=False, loc='lower left')
save(fig, 'F1_minimax_lower_bound')

# ── F2: single-round LFR vs p, 3 panels ──────────────────────────────────
sr = read_csv('single_round_all_codes.csv')
uf72_144 = read_csv('single_round_uf_decoder.csv')
uf288 = read_csv('single_round_uf_bb288.csv')
e1 = read_csv('rare_event_bposd.csv')
e6 = read_csv('bp_guided_matching_bb72.csv')

def get(rows, code, dec):
    sel = [r for r in rows if r['code'] == code and r['decoder'] == dec]
    sel.sort(key=lambda r: float(r['p']))
    return ([float(r['p']) for r in sel], [float(r['lfr']) for r in sel],
            [float(r['ci_lo']) for r in sel], [float(r['ci_hi']) for r in sel])

fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.5), sharex=True)
for ax, code in zip(axes, ['BB72', 'BB144', 'BB288']):
    for dec, color, mk in [('BP+OSD', C['bposd'], 'o'),
                           ('MWPM-DEM', C['mwpm'], 's'),
                           ]:
        plot_series(ax, *get(sr, code, dec), color, dec, marker=mk)
    uf_rows = uf288 if code == 'BB288' else uf72_144
    plot_series(ax, *get(uf_rows, code, 'UF-BFS'), C['uf'], 'UF-BFS', marker='^')
    # E1 rare-event overlay (10^6 trials)
    e1sel = [r for r in e1 if r['code'] == code]
    if e1sel:
        plot_series(ax,
                    [float(r['p']) for r in e1sel],
                    [float(r['lfr']) for r in e1sel],
                    [float(r['ci_lo']) for r in e1sel],
                    [float(r['ci_hi']) for r in e1sel],
                    '#2F4B7C', 'BP+OSD $10^6$ (E1)', marker='D')
    # E6 overlay on BB72 panel
    if code == 'BB72':
        plot_series(ax, *get(e6, code, 'BP-guided MWPM'), C['bpgm'],
                    'BP-guided MWPM (E6)', marker='P')
    ax.set_xscale('log'); ax.set_yscale('log')
    ax.set_ylim(1e-7, 1.5)
    ax.set_xlabel('physical error rate $p$')
    ax.set_title(code)
    ax.grid(alpha=0.25, linewidth=0.4, which='both')
axes[0].set_ylabel('logical failure rate')
axes[0].legend(frameon=False, loc='lower right')
fig.tight_layout()
save(fig, 'F2_single_round_lfr')

# ── F3: repeated-cycle adaptive (E3) ─────────────────────────────────────
fig, ax = plt.subplots(figsize=(3.5, 2.6))
for code, color, mk in [('BB72', C['bposd'], 'o'), ('BB144', C['uf'], '^'),
                        ('BB288', C['mwpm'], 's')]:
    rows = read_csv(f'repeated_cycle_adaptive_{code.lower()}.csv')
    rows.sort(key=lambda r: float(r['p']))
    plot_series(ax,
                [float(r['p']) for r in rows], [float(r['lfr']) for r in rows],
                [float(r['ci_lo']) for r in rows], [float(r['ci_hi']) for r in rows],
                color, f"{code} ($d$={rows[0]['rounds']})", marker=mk)
    for r in rows:
        ax.annotate(f"{int(r['trials'])//1000}k",
                    (float(r['p']), max(float(r['lfr']), float(r['ci_hi']))),
                    textcoords='offset points', xytext=(0, 4),
                    ha='center', fontsize=5.5, color=color, alpha=0.85)
ax.set_xscale('log'); ax.set_yscale('log')
ax.set_xlabel('physical error rate $p$')
ax.set_ylabel('logical failure rate per $d$ rounds')
ax.set_title('Repeated-cycle BP+OSD (adaptive budget; labels = trials used)')
ax.grid(alpha=0.25, linewidth=0.4, which='both')
ax.legend(frameon=False, loc='lower right')
fig.tight_layout()
save(fig, 'F3_repeated_cycle_adaptive')

# ── F4: hardware ablation, horizontal bars (rejected-Fig.7 fix) ──────────
rows = read_csv('hardware_ablations.csv')
label_map = {
    'CZ: full model': 'CZ-full',
    'CZ: no SWAP': 'CZ$-$SWAP',
    'CZ: no idle noise': 'CZ$-$idle',
    'CZ: no meas noise': 'CZ$-$meas',
    'CZ: gate decoherence only': 'CZ-gate-only',
    'Phenomenological': 'Phenom',
    'MS: full model': 'MS-full',
    'MS: CZ-matched gate': 'MS-CZ-matched',
}
order = ['CZ-full', 'CZ$-$SWAP', 'CZ$-$idle', 'CZ$-$meas', 'CZ-gate-only',
         'Phenom', 'MS-full', 'MS-CZ-matched']
vals = {label_map[r['condition']]: r for r in rows}
y = np.arange(len(order))[::-1]
lfr = [float(vals[k]['lfr']) for k in order]
lo = [float(vals[k]['ci_lo']) for k in order]
hi = [float(vals[k]['ci_hi']) for k in order]
colors = [C['cz'] if k.startswith('CZ') else (C['ms'] if k.startswith('MS')
          else C['pheno']) for k in order]
fig, ax = plt.subplots(figsize=(3.5, 2.6))
ax.barh(y, lfr, height=0.62, color=colors, alpha=0.85)
for yi, l, l_, h_ in zip(y, lfr, lo, hi):
    if l > 0:
        ax.plot([l_, h_], [yi, yi], color='k', linewidth=0.8)
        ax.plot([l_, l_], [yi - 0.18, yi + 0.18], color='k', linewidth=0.8)
        ax.plot([h_, h_], [yi - 0.18, yi + 0.18], color='k', linewidth=0.8)
    else:  # zero failures: open down-triangle at one-sided upper
        ax.plot([h_], [yi], marker='v', mfc='none', mec='k', mew=0.9,
                linestyle='none')
ax.set_yticks(y, order)
ax.set_xlabel('logical failure rate (3000 trials, $p_{base}=5\\times10^{-4}$)')
ax.set_xscale('log')
ax.set_xlim(5e-4, 3e-2)
ax.grid(alpha=0.25, linewidth=0.4, axis='x')
fig.tight_layout()
save(fig, 'F4_hardware_ablation')

# ── F5: three-backend comparison ─────────────────────────────────────────
rows = read_csv('hardware_three_condition_comparison.csv')
fig, ax = plt.subplots(figsize=(3.5, 2.5))
for backend, color, mk in [('Phenomenological', C['pheno'], 'o'),
                           ('CZ', C['cz'], 's'), ('MS', C['ms'], '^')]:
    sel = [r for r in rows if r['backend'] == backend]
    sel.sort(key=lambda r: float(r['p']))
    plot_series(ax,
                [float(r['p']) for r in sel], [float(r['lfr']) for r in sel],
                [float(r['ci_lo']) for r in sel], [float(r['ci_hi']) for r in sel],
                color, backend, marker=mk)
ax.set_xscale('log'); ax.set_yscale('log')
ax.set_xlabel('base error rate $p$')
ax.set_ylabel('logical failure rate')
ax.grid(alpha=0.25, linewidth=0.4, which='both')
ax.legend(frameon=False, loc='upper left')
fig.tight_layout()
save(fig, 'F5_three_backend')

# ── F6: correctability contrast (E0) ─────────────────────────────────────
rows = read_csv('correctability_by_weight.csv')
decs = ['radius-2 lookup', 'BP-guided MWPM', 'MWPM-DEM', 'UF-BFS']
dcolors = [C['lookup'], C['bpgm'], C['mwpm'], C['uf']]
ws = [0, 1, 2, 3]
fig, ax = plt.subplots(figsize=(3.5, 2.6))
width = 0.19
for i, (d, c) in enumerate(zip(decs, dcolors)):
    vals, los, his = [], [], []
    for w in ws:
        r = next(x for x in rows if x['decoder'] == d and int(x['weight']) == w)
        vals.append(float(r['correctability']))
        los.append(vals[-1] - (1 - float(r['ci_hi'])))
        his.append((1 - float(r['ci_lo'])) - vals[-1])
    xs = np.arange(len(ws)) + (i - 1.5) * width
    ax.bar(xs, vals, width=width, color=c, alpha=0.88, label=d)
    ax.errorbar(xs, vals, yerr=[los, his], fmt='none', ecolor='k',
                elinewidth=0.6, capsize=1.5)
ax.set_xticks(np.arange(len(ws)), [f'w={w}' for w in ws])
ax.set_ylabel('correctability (fraction corrected)')
ax.set_xlabel('error weight (Z patterns, BB72)')
ax.set_ylim(0, 1.09)
ax.grid(alpha=0.25, linewidth=0.4, axis='y')
ax.legend(frameon=False, loc='upper right', fontsize=6)
fig.tight_layout()
save(fig, 'F6_correctability_contrast')

# ── F7: graphification penalty ratio vs p (delta-method CIs) ─────────────
def ratio_delta(km, nm, kb, nb):
    """log-ratio LFR_MWPM/LFR_BPOSD with delta-method 95% CI."""
    if km == 0 or kb == 0:
        return None
    r = (km / nm) / (kb / nb)
    se = math.sqrt(1 / km - 1 / nm + 1 / kb - 1 / nb)
    return r, math.exp(math.log(r) - 1.96 * se), math.exp(math.log(r) + 1.96 * se)

fig, ax = plt.subplots(figsize=(3.5, 2.5))
for code, color, mk in [('BB72', C['bposd'], 'o'), ('BB144', C['uf'], '^'),
                        ('BB288', C['mwpm'], 's')]:
    pts = []
    for r in [x for x in sr if x['code'] == code and x['decoder'] == 'MWPM-DEM']:
        p = float(r['p'])
        km, nm = int(r['failures']), int(r['trials'])
        # prefer E1 10^6-trial denominator where available (p=0.002/0.004)
        e1r = next((x for x in e1 if x['code'] == code and
                    abs(float(x['p']) - p) < 1e-12), None)
        if e1r is not None and int(e1r['failures']) > 0:
            kb, nb = int(e1r['failures']), int(e1r['trials'])
        else:
            b = next(x for x in sr if x['code'] == code and
                     x['decoder'] == 'BP+OSD' and abs(float(x['p']) - p) < 1e-12)
            kb, nb = int(b['failures']), int(b['trials'])
        est = ratio_delta(km, nm, kb, nb)
        if est:
            pts.append((p, *est))
        else:
            # lower bound only: ratio >= MWPM point estimate / BPOSD upper
            bhi = (float(e1r['ci_hi']) if e1r is not None else
                   wilson_one_sided_upper(0, nb, z=1.96))
            ax.plot([p], [(km / nm) / bhi], marker='^', mfc='none',
                    mec=color, mew=0.9, linestyle='none')
    pts.sort()
    if pts:
        ps = [q[0] for q in pts]; rr = [q[1] for q in pts]
        lo = [q[1] - q[2] for q in pts]; hi = [q[3] - q[1] for q in pts]
        ax.errorbar(ps, rr, yerr=[lo, hi], color=color, marker=mk, capsize=2,
                    elinewidth=0.7, label=code)
ax.axhline(1.0, color='k', linewidth=0.6, linestyle='--', alpha=0.6)
ax.set_xscale('log'); ax.set_yscale('log')
ax.set_xlabel('physical error rate $p$')
ax.set_ylabel('penalty ratio  LFR$_{MWPM-DEM}$ / LFR$_{BP+OSD}$')
ax.grid(alpha=0.25, linewidth=0.4, which='both')
ax.legend(frameon=False, loc='lower left')
fig.tight_layout()
save(fig, 'F7_graphification_penalty_ratio')

print("ALL FIGURES DONE")
