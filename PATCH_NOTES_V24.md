# QAE v24 — Patch Notes

Engineering changelog for the v24 revision. The scientific finding-by-finding
ledger is `RESPONSE_TO_REVIEW_V24.md`. v23 artifacts are preserved as the
reviewed record; invalid files are renamed, not deleted.

## Manuscript (v17-manuscript/main_v24.tex)

- **Repositioned**: new title ("Certified Adversarial Risk Bounds for Quantum
  Error-Correcting Memories…"), abstract rewritten (250 words), claims list
  re-led by the certified-bounds claim; minimax saddle point and
  Knill–Laflamme floor explicitly labelled acknowledged background.
- **New remarks**: `rem:central-estimand` (fixed-implementation adversarial
  risk λ_M(W) as the central estimand), `rem:intervals` (simultaneous
  [L_W,U_W] reporting convention, honest U_W=1, Bonferroni joint ≥95%, exact
  Clopper–Pearson at zero counts, Howard confidence sequences for adaptive
  stopping), `rem:zerofail` (exact CP 2.996/N vs anti-conservative Wilson).
- **New tables**: `tab:priorart` (9-row prior-art positioning, R1–R9),
  `tab:injbound` (v24 injection-boundary cross-decoder summary).
- **Rewritten subsections**: §5.4 RC grid + adaptive ladder (v24-aligned
  priors, extended grid 0.001–0.012, p=0.010 rung), Λ paragraph (per-BLOCK
  cube-root statistic, unresolvable second rung, v23 numbers superseded),
  §8 Arm A framing (DEM re-analysis, not raw shots), §9 idle-noise null
  result, §10 certification reading (threat model + scoped evidence profile;
  QMAL ladder removed), conclusions, claim-to-evidence map (longtable).
- **§5.5**: verification-architecture paragraph (sectorwise sufficiency,
  independent trusted checker, published witness schema, syndrome-consistency
  assertions).
- **§6.6**: exact one-sided Clopper–Pearson zero-failure bounds replace Wilson
  everywhere at k=0; joint risk-ratio construction at 97.5%/97.5% → joint
  ≥95% (comparator BB72/BB288 ratio ">134,000×").
- **C03 repair**: mask-conditioned estimand; falsification verdict withdrawn;
  composed Binomial⊗Poisson model relabelled discovery (App. C findings
  i/iii/iv rewritten; `tab:injstoch` now 8 columns with both naive variants).
- **C01 disclosure**: limitation item documenting the reversed-extraction
  defect and its correction.

## Data artifacts (qae_experiments/data/)

- `repeated_cycle_{bposd,bb288_bposd,all_codes}_v24.csv` — fixed grid, v24
  priors (`model_rev=v24-aligned-priors`), extended to p=0.001/0.002.
- `repeated_cycle_adaptive_{bb72,bb144,bb288}_v24.csv` — 4-point adaptive
  ladder, seed tag `E3v24`.
- `repeated_cycle_adaptive_p010_*_v24.csv` — p=0.010 rung, seed tag
  `E3v24p010` (BB72 64/4000; BB144 2/20000; BB288 0/20000).
- `lambda_ladder_v24.csv` — 15 rows; per-BLOCK ratios; two-sided log-method
  CIs where both counts >0, one-sided exact-CP lower bounds otherwise.
- `injection_boundary_decoders_v24.csv` (168), `injection_boundary_mcnemar_v24.csv`
  (252), `inj_radius_noiseless_v24.csv` (16) — v24 IBD campaign.
- `rep_exact_{lfr,masks}_v24.csv` (30, 168) — REP3 exact stratification.
- `twirling_residual_v24.csv` (8) — analytic twirling closure residuals.

## Comparator (comparator/)

- `results/wsc_circuit_v23_reversed_extraction_INVALID.csv` — renamed v23
  record; `results/WSC_V23_INVALID.md` — withdrawal note.
- `wsc_circuit_point.py` — corrected CSS extraction (`circuit_rev =
  v24-corrected-extraction`), resume-capable, per-point DEM SHA-256 recorded.
- `wsc_verify.py` + `results/wsc_verify_report.json` — protocol-invariance
  tests T1–T4 (gadget parity, codespace silence, injection-column alignment,
  detector/observable audit): ALL PASS.
- `results/wsc_circuit.csv` / `wsc_circuit_v24.csv` — corrected grid (regenerated
  point-by-point; p=0.001 complete at 20,000 shots × 5 decoders at freeze time).

## Theory-test consolidation (theory_test_consol/)

- `run_stoch_reanalysis_v24.py` + `results/stoch_reanalysis_v24.{csv,json}` —
  fixed-mask reanalysis; concludes the v23 "naive bound falsified" verdict is
  NOT SUPPORTED under the correct estimand and is withdrawn.

## Reproducibility (qae_experiments/)

- `reproduce_all.py` — v24 master script (certificate → minimax → IBD → REP
  exact → twirling → RC grids → stoch reanalysis → WSC verify → Λ →
  validators → hashes); `--quick`, `--skip-adaptive`, `--skip-ibd` modes;
  hardware paths never invoked. v16 suite preserved as
  `reproduce_all_v16_legacy.py`.
- `validate_table_shapes.py` — v24 row expectations for all 16 new CSVs plus
  sibling-pipeline presence gates (WSC v24 CSV, verify report, stoch
  reanalysis).
- `requirements.txt` — v24 lock (numpy 2.5.2, scipy 1.18.1, stim 1.16.0,
  ldpc 2.4.1, pymatching 2.2.2, relay-bp 0.2.2, pandas 3.0.5,
  matplotlib 3.11.1).
- `gen_manifest.py` / `verify_hashes.py` — scope widened to the full archive/
  tree (1,600 files pinned at freeze time).
- `compute_lambda_v24.py` — per-BLOCK Λ with exact-CP ratio bounds
  (scipy beta.ppf; no comb() overflow at n=20,000).
- `ibm_demo_common.py` vendored at archive root for the offline hardware
  artifact readers.
