#!/usr/bin/env python3
"""wsc_figure.py — WS-C circuit-level corroboration: LER vs p for 5 decoders
on the synthetic BB72 circuit DEM + the nomatch (undecomposable) rate for
MWPM-stim. Output: figures/cmp_f3_wsc.{pdf,png}"""
import os
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE = os.path.abspath(os.path.dirname(__file__))
df = pd.read_csv(os.path.join(HERE, 'results', 'wsc_circuit.csv'))
PAL = {'BP+OSD':'#2166ac','Relay-BP':'#b2182b','MWPM-chain':'#878787','MWPM-stim':'#000000','BeliefMatch':'#1a9850'}
MRK = {'BP+OSD':'o','Relay-BP':'s','MWPM-chain':'v','MWPM-stim':'x','BeliefMatch':'P'}
fig,(ax1,ax2) = plt.subplots(1,2,figsize=(9.8,3.9))
ps = sorted(df.p.unique())
for name,g in df.groupby('decoder'):
    g=g.sort_values('p')
    ax1.errorbar(g.p,g.ler,yerr=[g.ler-g.ci_lo,g.ci_hi-g.ler],color=PAL[name],
                 marker=MRK[name],ms=5,lw=1.5,capsize=2.5,label=name)
    ax2.plot(g.p,g.no_matching/g.shots,color=PAL[name],marker=MRK[name],ms=5,lw=1.5,label=name)
ax1.set_yscale('log'); ax1.set_xscale('log')
ax1.set_xticks(ps); ax1.set_xticklabels([f'{p:g}' for p in ps],fontsize=7.5,rotation=25); ax1.minorticks_off()
ax1.set_xlabel('physical error rate p (circuit-level, 4 rounds)'); ax1.set_ylabel('logical error rate (20,000 shots)')
ax1.set_title('(a) BB72 Z-memory under circuit-level noise',fontsize=10,loc='left')
ax1.grid(alpha=0.25,which='both'); ax1.legend(fontsize=7.4,loc='center right')
ax2.set_xscale('log'); ax2.set_xticks(ps); ax2.set_xticklabels([f'{p:g}' for p in ps],fontsize=7.5,rotation=25); ax2.minorticks_off()
ax2.set_xlabel('physical error rate p'); ax2.set_ylabel('fraction of shots with no perfect matching')
ax2.set_title('(b) Matching-decoder coverage failure\n(undecomposable correlated mechanisms)',fontsize=10,loc='left')
ax2.grid(alpha=0.25); ax2.set_ylim(-0.02,1.05)
fig.tight_layout()
os.makedirs(os.path.join(HERE,'figures'),exist_ok=True)
for ext in ('pdf','png'): fig.savefig(os.path.join(HERE,'figures',f'cmp_f3_wsc.{ext}'),dpi=200)
print('saved figures/cmp_f3_wsc')
