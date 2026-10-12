"""
ap03_ab_figure.py — Figure AP-2: active-provenance A/B hardware result.

Panels:
  (a) Layout schematic: used line q0..q10, A-line vs B-line for REP3/REP5,
      defect annotations (q1 readout 3.43x snapshot; q3 hottest ancilla).
  (b) Logical error rate A vs B per configuration, Wilson 95% CI, log scale;
      per-config z and CMH pooled z = -1.73 (one-sided p = 0.042).
  (c) Mean ancilla detection rate per configuration, A vs B — REP3 balanced,
      REP5 B-line higher (q9 under-modeled): honest model-mismatch disclosure.
"""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

R = json.load(open('results/ap_ab_decode_detail.json'))
CFG = ['REP3-Z', 'REP3-X', 'REP5-Z', 'REP5-X']
LINES = {('REP3', 'A'): [0, 1, 2, 3, 4], ('REP3', 'B'): [2, 3, 4, 5, 6],
         ('REP5', 'A'): list(range(0, 9)), ('REP5', 'B'): list(range(2, 11))}

C_A = '#2166ac'   # consistent with ap_f1 palette
C_B = '#b2182b'
C_GREY = '#666666'

fig = plt.figure(figsize=(10.6, 3.7))
gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 1.0, 1.0], wspace=0.32,
                      left=0.045, right=0.99, top=0.84, bottom=0.14)

# ------------------------------------------------------------------ (a) layout
axa = fig.add_subplot(gs[0])
axa.set_xlim(-1.75, 10.6)
axa.set_ylim(-0.28, 3.75)
axa.axis('off')
axa.set_title('(a) A/B line layouts', fontsize=10, loc='left')

for q in range(11):
    axa.add_patch(plt.Circle((q, 3.30), 0.16, color='#dddddd', zorder=2))
    axa.text(q, 3.58, f'q{q}', ha='center', fontsize=7.5, color=C_GREY)
rows = [('REP5  B', 2.55, LINES[('REP5', 'B')], C_B),
        ('REP5  A', 2.00, LINES[('REP5', 'A')], C_A),
        ('REP3  B', 1.20, LINES[('REP3', 'B')], C_B),
        ('REP3  A', 0.65, LINES[('REP3', 'A')], C_A)]
for label, y, line, col in rows:
    axa.plot(line, [y] * len(line), '-', color=col, lw=5, alpha=0.35,
             solid_capstyle='round', zorder=3)
    for q in line:
        axa.add_patch(plt.Circle((q, y), 0.13, color=col, zorder=4))
    axa.text(-1.65, y, label, ha='left', va='center', fontsize=8.5, color=col,
             fontweight='bold')
# defect annotations anchored to the ghost row
axa.annotate('q1: readout defect\n3.43× snapshot', xy=(1, 3.30), xytext=(-1.1, -0.18),
             fontsize=7.5, color=C_GREY, ha='left',
             arrowprops=dict(arrowstyle='-', color=C_GREY, lw=0.8,
                             connectionstyle='arc3,rad=-0.25'))
axa.annotate('q3: hottest ancilla\n(physical defect map)', xy=(3, 3.30), xytext=(5.3, -0.18),
             fontsize=7.5, color=C_GREY, ha='left',
             arrowprops=dict(arrowstyle='-', color=C_GREY, lw=0.8,
                             connectionstyle='arc3,rad=0.25'))

# ------------------------------------------------------------------ (b) LER A/B
axb = fig.add_subplot(gs[1])
x = np.arange(len(CFG))
w = 0.38
for k, (arm, col) in enumerate([('A', C_A), ('B', C_B)]):
    ler = np.array([R['configs'][c][arm]['ler'] for c in CFG])
    lo = np.array([R['configs'][c][arm]['lo'] for c in CFG])
    hi = np.array([R['configs'][c][arm]['hi'] for c in CFG])
    fails = [R['configs'][c][arm]['fails'] for c in CFG]
    xx = x + (k - 0.5) * w
    axb.bar(xx, np.maximum(ler, 6e-5), w * 0.88, color=col, alpha=0.85, zorder=3,
            label='A-line (original)' if arm == 'A' else 'B-line (metrology-selected)')
    axb.errorbar(xx, np.maximum(ler, 6e-5),
                 yerr=[np.maximum(ler - lo, 0), np.maximum(hi - ler, 0)],
                 fmt='none', ecolor='black', elinewidth=1.0, capsize=2.5, zorder=4)
    for xi, l, h, f in zip(xx, ler, hi, fails):
        ytxt = max(h * 1.25, 8e-5)
        axb.text(xi, ytxt, f'{f}/10⁴', ha='center', fontsize=7.2, color=col)
axb.set_yscale('log')
axb.set_ylim(5e-5, 3e-2)
axb.set_xticks(x)
axb.set_xticklabels(CFG, fontsize=9)
axb.set_ylabel('logical error rate (r = 4)', fontsize=9)
axb.set_title('(b) LER: B ≤ A in all four configs', fontsize=10, loc='left')
axb.grid(axis='y', alpha=0.25, zorder=0)
axb.legend(fontsize=7.4, loc='upper right', framealpha=0.95)
axb.text(0.52, 0.40, 'CMH pooled z = −1.73\n(one-sided p = 0.042)',
         transform=axb.transAxes, fontsize=8, color=C_GREY, ha='center',
         bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='#cccccc', lw=0.6))

# ------------------------------------------------------------------ (c) det rates
axc = fig.add_subplot(gs[2])
detA, detB = [], []
for c in CFG:
    detA.append(np.mean([np.mean(rd) for rd in R['configs'][c]['A']['det']]))
    detB.append(np.mean([np.mean(rd) for rd in R['configs'][c]['B']['det']]))
axc.bar(x - w / 2, detA, w * 0.88, color=C_A, alpha=0.85, zorder=3, label='A-line')
axc.bar(x + w / 2, detB, w * 0.88, color=C_B, alpha=0.85, zorder=3, label='B-line')
for xi, (a, b) in enumerate(zip(detA, detB)):
    axc.annotate(f'{a:.3f}', (xi - w / 2, a), textcoords='offset points',
                 xytext=(0, 3), ha='center', fontsize=7.2, color=C_A)
    axc.annotate(f'{b:.3f}', (xi + w / 2, b), textcoords='offset points',
                 xytext=(0, 3), ha='center', fontsize=7.2, color=C_B)
axc.set_xticks(x)
axc.set_xticklabels(CFG, fontsize=9)
axc.set_xlim(-0.6, 3.75)
axc.set_ylabel('mean ancilla detection rate', fontsize=9)
axc.set_ylim(0, 0.115)
axc.set_title('(c) Detection rate: REP3 balanced', fontsize=10, loc='left')
axc.grid(axis='y', alpha=0.25, zorder=0)
axc.text(0.03, 0.90, 'REP5 B-line higher (z = +3.69/+3.87):\nq9 under-modeled — disclosed limitation',
         transform=axc.transAxes, fontsize=7.5, color=C_GREY, va='top')

fig.savefig('figures/ap_f2_ab_result.pdf')
fig.savefig('figures/ap_f2_ab_result.png', dpi=220)
print('saved figures/ap_f2_ab_result.{pdf,png}')
