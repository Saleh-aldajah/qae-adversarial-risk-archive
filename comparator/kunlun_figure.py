import os, json, hashlib, numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE = os.path.abspath(os.path.dirname(__file__))
import csv as _csv
PAL = {'BP-OSD':'#e08214','BP-only':'#542788','MWPM-prior':'#878787','BeliefMatch':'#1a9850','Relay-BP':'#b2182b'}
MRK = {'BP-OSD':'^','BP-only':'o','MWPM-prior':'v','BeliefMatch':'P','Relay-BP':'s'}
rows=[]
with open(os.path.join(HERE,'results','kunlun_cmp.csv')) as f:
    for r in _csv.DictReader(f):
        r['cycles']=int(r['cycles']); r['ler']=float(r['ler'])
        r['lo']=float(r['ci_lo']); r['hi']=float(r['ci_hi']); r['sec']=float(r['sec'])
        rows.append(r)
def wilson(f,n,z=1.96):
    if n==0: return (0,0)
    ph=f/n; d=1+z*z/n; c=ph+z*z/(2*n); m=z*np.sqrt(ph*(1-ph)/n+z*z/(4*n*n))
    return (c-m)/d,(c+m)/d
fig,axes = plt.subplots(1,2,figsize=(9.6,3.9))
ax=axes[0]
cycs = sorted({r['cycles'] for r in rows})
for dec in ['Relay-BP','BP-OSD','BP-only','BeliefMatch','MWPM-prior']:
    xs=[]; ys=[]; lo=[]; hi=[]
    for c in cycs:
        sel=[r for r in rows if r['decoder']==dec and r['cycles']==c]
        if not sel: continue
        lers=[r['ler'] for r in sel]; se=[r for r in sel if r['sector']=='X']; sz=[r for r in sel if r['sector']=='Z']
        # mean of sectors; CI from pooled counts
        f=sum(int(r['ler']*int(r['shots'])) for r in sel); n=sum(int(r['shots']) for r in sel)
        l,h=wilson(f,n)
        xs.append(c); ys.append(np.mean(lers)); lo.append(np.mean(lers)-l); hi.append(h-np.mean(lers))
    dodge = {'Relay-BP':-0.035,'BP-OSD':0.035}.get(dec,0.0)
    lab = {'BP-OSD':'BP-OSD (10$^4$ iter)'}.get(dec,dec)
    ax.errorbar([x+dodge for x in xs],ys,yerr=[lo,hi],marker=MRK[dec],color=PAL[dec],ms=6,lw=1.6,capsize=3,label=lab)
ax.set_yscale('log'); ax.set_xlabel('QEC rounds (Kunlun hardware experiment)'); ax.set_ylabel('Logical error rate (mean of X/Z)')
ax.set_xticks(cycs); ax.grid(alpha=0.25,which='both'); ax.legend(fontsize=7.6,loc='upper left',framealpha=0.9)
ax.set_title('(a) Five decoders on the published Kunlun\n18-qubit BB72 detector model (10,000 shots/point)')
ax=axes[1]
agg={}
for r in rows: agg.setdefault(r['decoder'],[]).append(r['sec'])
names=[d for d in ['Relay-BP','BP-OSD','BP-only','BeliefMatch','MWPM-prior'] if d in agg]
y=np.arange(len(names)); vals=[np.mean(agg[d]) for d in names]
ax.barh(y,vals,color=[PAL[d] for d in names],height=0.62,alpha=0.9)
ax.set_yticks(y); ax.set_yticklabels([{'BP-OSD':'BP-OSD (10$^4$ iter)'}.get(d,d) for d in names],fontsize=8); ax.invert_yaxis()
ax.set_xscale('log'); ax.set_xlabel('Wall time per 10,000-shot point (s, log)')
for yi,v in zip(y,vals):
    ax.text(v*1.12,yi,(f'{v:,.0f} s' if v>=1.5 else f'{v:.2f} s'),va='center',fontsize=8)
ax.set_title('(b) Decode cost (BP-based methods include\nper-point BP; BeliefMatch rebuilds graph per shot)')
ax.grid(alpha=0.25,axis='x')
fig.tight_layout()
for ext in ('pdf','png'):
    fig.savefig(os.path.join(HERE,'figures',f'cmp_f2_kunlun.{ext}'),dpi=200)
print('figure saved; rows used:',len(rows))
