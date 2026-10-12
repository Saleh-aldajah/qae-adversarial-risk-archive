# Patch Notes — v21 (2026-09-23)

Scope: closure of the four Tier-1 items from the external "honest
assessment" review. All new data were produced with the pinned
`stable_seed` policy and carry SHA-256 matrix digests; the v17 toolchain
(bit-identical seeds, ldpc 2.4.1 / pymatching 2.4.0) reproduced every
regenerated row exactly.

## E1 — Rare-event campaign (10^6 trials per point)

`run_e1_rare_event.py` regenerates `data/rare_event_bposd.csv`
(6 rows: BB72/BB144/BB288 x p in {0.002, 0.004}, 1,000,000 trials each).
Full re-run on 2026-09-23 reproduced all six archived rows exactly:
BB72 22/1M (p=0.002) and 160/1M (p=0.004); BB144 1/1M and 11/1M;
BB288 0/1M at both p. Consequences for the manuscript:

- Table tab:e1 (new): bounded BP+OSD LFRs at 10^6 trials.
- Risk ratios at p=0.004 become finite for all three codes:
  BB72 371.9x [312.7, 442.3]; BB144 17,500x [9,678, 31,643];
  BB288 > 183,000x (one-sided 95%).
- Bridge remark (rem:bridge-number): eps_FT^logical <= 3.2e-4 point,
  <= 3.74e-4 at 95% (was <= 2.0e-4 / <= 1.13e-3 from 10^4 trials).

## E3 — Adaptive repeated-cycle extension at p = 0.010

`run_e3_ext_p010.py` (derived from `run_e3_rc_adaptive.py`, protocol
identical) adds the missing grid point under the same pinned seeds:

- BB72 (d=6): 65/4,000 (stopped at >= 50 failures)
- BB144 (d=12): 4/20,000 — with 3/20,000 at p=0.008 and 14/20,000 at
  p=0.012 the adaptive BB144 tail is now monotone (3, 4, 14); the
  fixed-grid non-monotone pair (1/2,000 vs 0/2,000) is resolved at
  10x the trials without dropping data.
- BB288 (d=18): 1/20,000 — tail 0, 0, 0, 1, 2 (monotone).

Independent verification: `verify_e3_bb144_p012.py` re-ran the archived
BB144 p=0.012 adaptive row (all ten 2,000-trial batches, pinned batch
seeds) and reproduced 14/20,000 exactly.

## O5 — Exact BB72 distance d = 6

`verify_certificate.py` gains obligation O5: exhaustive weight-6 kernel
enumeration (meet-in-the-middle 3+3 over all C(72,3) = 59,640 triples per
sector; completeness follows because every weight-6 kernel vector splits
into two disjoint equal-syndrome triples). Result: 120 kernel candidates
per sector, 84 + 84 nontrivial weight-6 logicals, each syndrome-zero,
outside the opposite stabiliser row space, and anticommuting with at
least one opposite-sector weight-6 logical (2,592 anticommuting pairs;
lexicographically first witnesses (0,1,2,3,20,22) Z-type and
(0,3,6,12,27,30) X-type). With O3b excluding weight <= 5, BB72 is
certified [[72,12,6]] with d = 6 exactly.
`data/bb72_certificate_report.json` now records O1-O5; the script
regenerates it deterministically.

## Archive completeness fixes

- `data/` now ships the full E0-E6 evidence set (correctability_by_weight,
  single_round_uf_bb288, robustness_sweep_bb72, crosscheck_e5,
  bp_guided_matching_bb72, rare_event_bposd, adaptive RC CSVs) plus
  `legacy/` and `minimax_lower_bounds.csv`; the v20 zip carried the
  runners but only 8 CSVs.
- v16 infrastructure restored alongside the v17 tree: Dockerfile,
  Makefile, reproduce_all.py, reproduce_fast.py, environment.yml,
  requirements.txt, PATCH_NOTES_V16.md, FAST_VERIFICATION_LOG_V16.md.
- `validate_table_shapes.py` and `validate_seed_consistency.py` extended
  with the three p010 rows.
- `sha256_manifest.json` regenerated over the merged tree
  (`gen_manifest.py`).

Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
