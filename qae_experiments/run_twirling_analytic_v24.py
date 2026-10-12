#!/usr/bin/env python3
"""
run_twirling_analytic_v24.py — analytic diamond-distance closure for the
REP3 coherent-noise study (review Sec. 4.7; extends run_twirling_residual.py).

For the REP3 bit-flip code with majority-vote recovery under independent
X-rotation coherent noise exp(-i theta X/2) per qubit, the logical channel
in the Pauli transfer picture has, with s = sin(theta), c = cos(theta):

    p_L = 3 s^4 c^2 + s^6        (logical bit-flip probability)
    g   = 2 c^3 s^3              (coherent off-diagonal PTM element)

and the exact diamond distances (Watrous' theorem; the channel difference
is a Pauli channel conjugated by a Z-rotation, whose diamond norm is
attained on a basis state) are

    D(E_L, E_L^twirl) = 2|g|                        (to its Pauli twirl)
    D(E_L, id)        = 2 sqrt(p_L^2 + g^2)         (to the identity)

Derivation is given in the manuscript (Remark on the calibrated twirling
residual).  This script emits the analytic columns on the archived theta
grid, checks the archived variational estimates are lower bounds of the
exact values (they are variational lower estimates per review Sec. 4.7),
and reports the small-theta asymptotics 2|g| ~ 4 theta^3 and
D_id/(2 p_L) ~ 2/(3 theta).

Output: data/twirling_residual_v24.csv
"""
import csv, math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data"

src = OUT / 'twirling_residual.csv'
rows = []
with open(src) as f:
    for r in csv.DictReader(f):
        th = float(r['theta'])
        s, c = math.sin(th), math.cos(th)
        p_L = 3 * s**4 * c**2 + s**6
        g = 2 * c**3 * s**3
        d_twirl = 2 * abs(g)
        d_id = 2 * math.sqrt(p_L**2 + g**2)
        v_twirl = float(r['diamond_to_twirl'])
        v_id = float(r['diamond_to_id'])
        rows.append(dict(
            exp='twirling_residual_v24', theta=th,
            p_L_analytic=p_L, g_analytic=g,
            diamond_to_twirl_exact=d_twirl,
            diamond_to_id_exact=d_id,
            ratio_Did_over_2pL_exact=d_id / (2 * p_L),
            asymp_twirl_4theta3=4 * th**3,
            asymp_ratio_2_over_3theta=2 / (3 * th),
            variational_to_twirl=v_twirl,
            variational_to_id=v_id,
            variational_le_exact_twirl=int(v_twirl <= d_twirl * (1 + 2e-2)),
            variational_le_exact_id=int(v_id <= d_id * (1 + 2e-2)),
            archived_p_l_coh=r['p_l_coh'],
            p_l_matches_archive=abs(p_L - float(r['p_l_coh'])) <=
            2e-2 * max(p_L, 1e-300)))

ok_lb = all(r['variational_le_exact_twirl'] and r['variational_le_exact_id']
            for r in rows)
ok_pl = all(r['p_l_matches_archive'] for r in rows)
print('variational estimates within archived rounding of exact:', ok_lb)
print('analytic p_L within archived rounding of archived column:', ok_pl)
for r in rows:
    print(f"  th={r['theta']:.2f}  2|g|={r['diamond_to_twirl_exact']:.6f} "
          f"(4th^3={r['asymp_twirl_4theta3']:.6f})  "
          f"Did/2pL={r['ratio_Did_over_2pL_exact']:.3f} "
          f"(2/3th={r['asymp_ratio_2_over_3theta']:.3f})")

with open(OUT / 'twirling_residual_v24.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print('Saved twirling_residual_v24.csv', f'({len(rows)} rows)')
