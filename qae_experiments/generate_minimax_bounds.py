"""
generate_minimax_bounds.py  —  Regenerate minimax fidelity lower bounds.

Reproduces: data/minimax_lower_bounds.csv
Formula: (1-delta) * Pr[Bin(n,p) <= t]  with delta=0.1, n=128, d=11, t=5.
Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
import csv, math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT  = ROOT / "data"; OUT.mkdir(exist_ok=True)

n, d, t, delta = 128, 11, 5, 0.1

def binom_cdf(t, n, p):
    return sum(math.comb(n,i)*(p**i)*((1-p)**(n-i)) for i in range(t+1))

PS = [0.0,0.001,0.002,0.003,0.004,0.005,0.006,0.007,0.008,0.009,
      0.01,0.015,0.02,0.025,0.03,0.04,0.05,0.06,0.07,0.08,0.09,0.1]

rows = []
for p in PS:
    prob = binom_cdf(t, n, p)
    lb   = (1-delta)*prob
    rows.append(dict(n=n, delta=delta, d=d, t=t, p_attack=p,
                     lower_bound=round(lb,10), binomial_cdf=round(prob,10)))
    print(f"  p={p:.3f}: LB={lb:.6f}")

with open(OUT/'minimax_lower_bounds.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
print(f"\nSaved minimax_lower_bounds.csv  ({len(rows)} rows)")
