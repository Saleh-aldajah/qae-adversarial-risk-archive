"""
analyze_grid.py — post-grid statistics: paired McNemar tests between decoders
on identical error instances, per-p win/loss tables, and the comparator figure.

Inputs: results/comparator_grid.csv + results/failbits/{decoder}_{p}.npy
Outputs: results/comparator_mcnemar.csv + figures/cmp_f1_grid.{pdf,png}
"""
import os, sys, json, math
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FB = os.path.join(HERE, 'results', 'failbits')

PALETTE = {
    'BP+OSD': '#2166ac',
    'Relay-BP': '#b2182b',
    'symatch-bare': '#999999',
    'symatch-simplex': '#66c2a5',
    'symatch-pre+simplex': '#3288bd',
    'symatch-BP+simplex': '#e08214',
    'symatch-BP+pre+simplex': '#7b3294',
}
MARKERS = {'BP+OSD': 'o', 'Relay-BP': 's', 'symatch-bare': 'x',
           'symatch-simplex': '^', 'symatch-pre+simplex': 'v',
           'symatch-BP+simplex': 'D', 'symatch-BP+pre+simplex': 'P'}


def mcnemar(a, b):
    """a, b: fail-bit arrays (paired). Returns (b01, b10, z, p_two_sided).
    b01: instances a fails & b succeeds; b10: a succeeds & b fails."""
    b01 = int(np.sum((a == 1) & (b == 0)))
    b10 = int(np.sum((a == 0) & (b == 1)))
    n = b01 + b10
    if n == 0:
        return b01, b10, 0.0, 1.0
    # exact binomial two-sided p
    from math import comb
    k = min(b01, b10)
    p = min(1.0, 2 * sum(comb(n, i) for i in range(0, k + 1)) / 2**n)
    z = (b10 - b01) / math.sqrt(n)
    return b01, b10, z, p


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', default=os.path.join(HERE, 'results', 'comparator_grid.csv'))
    ap.add_argument('--tag', default='')
    args = ap.parse_args()
    df = pd.read_csv(args.csv)
    ps = sorted(df['p'].unique())
    keys = list(dict.fromkeys(df['decoder_key']))
    rows = []
    for p in ps:
        bits = {k: np.load(os.path.join(FB, f'{k}_{p}.npy')) for k in keys}
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                b01, b10, z, pv = mcnemar(bits[a], bits[b])
                rows.append(dict(p=p, dec_a=a, dec_b=b,
                                 a_fail_b_ok=b01, a_ok_b_fail=b10,
                                 z_b_minus_a=z, p_exact=pv))
    mc = pd.DataFrame(rows)
    mc.to_csv(os.path.join(HERE, 'results', f'comparator_mcnemar{args.tag}.csv'), index=False)
    print(mc.to_string(index=False, max_rows=80))

    # ---------------- figure: LER curves + runtime
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.4, 3.9),
                                   gridspec_kw=dict(width_ratios=[1.25, 1.0],
                                                    wspace=0.26,
                                                    left=0.06, right=0.985,
                                                    top=0.84, bottom=0.14))
    for _, g in df.groupby('decoder'):
        g = g.sort_values('p')
        name = g['decoder'].iloc[0]
        col = PALETTE.get(name, '#333333')
        mk = MARKERS.get(name, 'o')
        ax1.errorbar(g['p'], g['ler'],
                     yerr=[g['ler'] - g['ci_lo'], g['ci_hi'] - g['ler']],
                     color=col, marker=mk, ms=4, lw=1.4, capsize=2.5,
                     label=name)
        gs = g.dropna(subset=['sec'])
        if len(gs):
            ax2.plot(gs['p'], gs['sec'] / (gs['trials'] * 2) * 1e3, color=col,
                     marker=mk, ms=4, lw=1.4, label=name)
    ax1.set_yscale('log')
    ax1.set_xscale('log')
    ax1.set_xticks(ps)
    ax1.set_xticklabels([f'{p:g}' for p in ps], fontsize=8)
    ax1.set_xlabel('physical error rate p (single-round, both sectors)', fontsize=9)
    ax1.set_ylabel('logical error rate (10⁴ paired trials)', fontsize=9)
    ax1.set_title('(a) Pinned paired BB72 decoder grid', fontsize=10, loc='left')
    ax1.grid(alpha=0.25)
    ax1.legend(fontsize=7.2, loc='upper left')
    ax2.set_yscale('log')
    ax2.set_xscale('log')
    ax2.set_xticks(ps)
    ax2.set_xticklabels([f'{p:g}' for p in ps], fontsize=7.5, rotation=25)
    ax2.minorticks_off()
    ax2.set_xlabel('physical error rate p', fontsize=9)
    ax2.set_ylabel('mean decode time (ms/sector-decode)', fontsize=9)
    ax2.set_title('(b) Decode-time comparison', fontsize=10, loc='left')
    ax2.grid(alpha=0.25)
    os.makedirs(os.path.join(HERE, 'figures'), exist_ok=True)
    fig.savefig(os.path.join(HERE, 'figures', f'cmp_f1_grid{args.tag}.pdf'))
    fig.savefig(os.path.join(HERE, 'figures', f'cmp_f1_grid{args.tag}.png'), dpi=220)
    print(f'saved figures/cmp_f1_grid{args.tag}.{{pdf,png}}')


if __name__ == '__main__':
    main()
