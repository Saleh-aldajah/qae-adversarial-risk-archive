# PATCH NOTES — v23 (2026-09-24)

Two calibrated experiments closing stated Limitations, plus the
Extension-1 hardware runner (delivered earlier this turn and unchanged
here).  Manuscript: `main_v23.tex`; all data deterministic and pinned.

## Experiment 1 — cross-decoder injection-boundary calibration
`run_inj_boundary_decoders.py` -> `data/injection_boundary_decoders.csv`
(126 rows; single-round phenomenological, p = 0.003; controls 8,000
trials, certified halves 4,000; seeds `stable_seed('IBD', ...)`).

Replays the Theorem-3 probe matrix (W <= 2 controls vs O5-certified
weight-3 halves of weight-6 logicals) under BP+OSD, Union-Find, and
BP-guided MWPM:

- BP+OSD preserves the certified boundary: max control LFR 6.8% (X) /
  7.1% (Z) vs certified pair-maxima 92-95%  (contrast >= 13x).
- Union-Find and BP-guided MWPM collapse the boundary from below:
  control LFR >= 99% already at weight 2 (contrast 1.0x).
- All three decoders saturate the certified halves at >= 92%.

Conclusion written into Remark rem:crossdec: radius-completeness of the
decoder is a *security* property; the adversarial work factor t+1 = 3
(Corollary cor:workfactor) is realised by BP+OSD but degrades to W ~ 1
for non-radius-complete graph decoders.

## Experiment 2 — calibrated twirling residual (REP3)
`run_twirling_residual.py` -> `data/twirling_residual.csv` (8 rows;
deterministic linear algebra, seeded Watrous maximisation).

Exact logical channel of the REP3 bit-flip memory under coherent
axis-aligned noise U = exp(-i theta X), ideal extraction + majority-vote
recovery:

- LFR is twirl-exact: p_coh / p_twirl = 1.000 for all theta <= 0.3.
- Residual logical rotation cubic: theta_L ~= -2 theta^3;
  ||E_L - E_L^twirl||_diamond ~= 4 theta^3.
- Bridge ratio ||E_L - id||_diamond / (2 LFR) ~= 2/(3 theta), growing
  33.3 -> 2.3 over theta = 0.02 -> 0.30: outside the Pauli class no
  theta-independent bridge exists; within it prop:bridge is exact.

Written into Remark rem:twirl-num; Limitations items on the bridge and
on the LFR proxy now carry the quantified caveat.

## Manuscript changes (v22 -> v23)
1. New Remark rem:crossdec after rem:decoder-inst.
2. New Remark rem:twirl-num after rem:bridge-number.
3. Limitations: bridge item and LFR-proxy item updated to reference the
   calibrated residual.
4. Claim map: diamond-bridge row updated; +2 rows (cross-decoder
   boundary, twirling residual).

## Validation
- run_inj_boundary_decoders.py: 126 rows, deterministic seeds.
- run_twirling_residual.py: 8 rows, deterministic.
- validate_table_shapes.py: +2 expectations (126, 8 rows).
- MANIFEST regenerated; verify_hashes: 0 failures.
