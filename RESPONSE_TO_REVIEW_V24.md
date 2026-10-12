# QAE v24 — Point-by-Point Response Ledger

Maps each finding of the v23 Scientific Review and Improvement Plan to the
action taken and the artifact that evidences it. "Manuscript" refers to
`v17-manuscript/main_v24.tex`.

## C01 — WS-C circuit used reversed CSS extraction (critical)

- **Action**: extraction convention corrected; four protocol-invariance test
  groups implemented (T1 gadget parity — reversed primitives return
  input-independent 0; T2 codespace silence; T3 injection-column alignment
  with H_Z/H_X; T4 detector/observable map audit). All PASS. v23 CSV renamed
  `wsc_circuit_v23_reversed_extraction_INVALID.csv` with withdrawal note
  `WSC_V23_INVALID.md`; corrected grid regenerated with
  `circuit_rev=v24-corrected-extraction` and per-point DEM SHA-256.
- **Artifacts**: `comparator/wsc_verify.py`,
  `comparator/results/wsc_verify_report.json`,
  `comparator/results/wsc_circuit_v24.csv`; manuscript §8 Arm B + limitation
  item disclosing the defect.

## C03 — "Naive bound falsified" verdict used the wrong estimand (critical)

- **Action**: reanalysis under the pinned mask-conditioned estimand
  (threshold = d0_hi + realized_tail + TOL_STOCH). Reviewer thresholds
  reproduced exactly (0.022384/0.042729 campaign 1; 0.022384/0.042566
  consolidation). No realized LER exceeds its threshold in any cell
  (0.0211/0.0388; 0.0202/0.0403). **Falsification withdrawn**; the composed
  Binomial⊗Poisson model is relabelled a *discovery* with the consolidation
  campaign as its confirmatory test.
- **Artifacts**: `theory_test_consol/run_stoch_reanalysis_v24.py`,
  `results/stoch_reanalysis_v24.{csv,json}`; manuscript App. C findings
  (i)/(iii)/(iv), `tab:injstoch` (8-column), abstract, claims, conclusion.

## C06 — π bound presented as conservative envelope

- **Action**: π re-framed as the prediction of a pinned model (Poisson
  fault-count law over readout-error locations), explicitly *not* a
  conservative envelope; device-aware composition stated as a corollary.
- **Artifacts**: manuscript App. A model-status paragraph, `cor:stoch`.

## Statistics at zero counts (review §6.6)

- **Action**: all zero-failure upper bounds switched to exact one-sided
  Clopper–Pearson 1−0.05^(1/N) ≈ 2.996/N; Wilson-at-zero documented as
  anti-conservative; joint risk-ratio lower bounds constructed at 97.5% per
  side → joint ≥95% (Bonferroni); adaptive ladder governed by pinned stopping
  with confidence-sequence justification.
- **Artifacts**: manuscript `rem:zerofail`, `rem:intervals`, `tab:sr_bposd`,
  `tab:uf`, `tab:e1`, `tab:rc`, `tab:rc_adaptive`; `compute_lambda_v24.py`.

## RC ladder priors misaligned (v23 spacetime matrices)

- **Action**: v24 rerun with exactly aligned priors
  (`model_rev=v24-aligned-priors`); fixed grid extended to 0.001–0.012;
  adaptive ladder re-run with seed tag `E3v24` plus a p=0.010 rung
  (`E3v24p010`); v23 BB144 tail does not reproduce and is superseded.
- **Artifacts**: `run_rc_only_v24.py`, `run_e3_rc_adaptive_v24.py`,
  `run_e3_rc_adaptive_v24_p010.py`, the six v24 CSV families; manuscript
  `tab:rc`, `tab:rc_adaptive`.

## Λ definition and comparability (review §7)

- **Action**: Λ defined as the cube root of the per-BLOCK failure ratio
  (block = d rounds); explicit statement that the protocol is not matched to
  Acharya et al.'s per-cycle circuit-level Λ=2.14 and no absolute-performance
  comparison is claimed; BB144→BB288 rung reported as statistically
  unresolvable at 20,000 trials with no point estimate; combined 6→18 bounds
  reported one-sided.
- **Artifacts**: `lambda_ladder_v24.csv` (15 rows); manuscript Λ paragraph.

## Injection-boundary cross-decoder claims (v23 IBD)

- **Action**: full v24 recampaign — noiseless exhaustive w≤2 wrong-logical per
  sector (BP+OSD 0/0, MW-lookup 0/0, UF 13/0, BP-guided 0/3), noisy W≤2
  controls, invalid-residual shares, McNemar pairing, certified-halves
  analysis; prose corrected to the control-set definition (44–58%, 71–98% at
  weight 2).
- **Artifacts**: `injection_boundary_decoders_v24.csv`,
  `injection_boundary_mcnemar_v24.csv`, `inj_radius_noiseless_v24.csv`;
  manuscript `tab:injbound`, `rem:crossdec`.

## C08 — Reproducibility gaps

- **Action**: single offline master script covering all v24 artifacts;
  validators extended (16 new CSVs + sibling-pipeline gates); dependency lock
  updated; manifest scope widened to the whole archive (1,600 files); IBM
  helper vendored; hardware paths excluded from offline reproduction.
- **Artifacts**: `reproduce_all.py`, `validate_table_shapes.py`,
  `validate_seed_consistency.py`, `requirements.txt`, `gen_manifest.py`,
  `verify_hashes.py`, `sha256_manifest.json`.

## C11 — QMAL ladder overclaimed

- **Action**: QMAL maturity ladder removed; replaced by a scoped
  integrity-evidence profile (code certificate, radius exhaustiveness,
  benchmark grid, device campaigns, provenance) with an explicit threat model
  (protected asset, trust boundary, adversary class). The QMAL-5 two-device
  claim corrected: active provenance ran on ibm_marrakesh only; fez
  replicated injection bounds. QEC-is-not-authentication cited
  (Barnum et al. 2002; Portmann 2017); SHA-256 framing corrected to artifact
  integrity vs a trusted archive.
- **Artifacts**: manuscript §10 (`ssec:qmic`), claims, conclusion.

## §5.5 certificate robustness

- **Action**: verification-architecture paragraph — sectorwise sufficiency
  for mixed Paulis, independent self-contained trusted checker (334 lines,
  exits nonzero on any mismatch), published witness schema enabling
  linear-time third-party checks of d=6, syndrome-consistency assertions.
- **Artifacts**: manuscript §5.5; `verify_certificate.py` (ALL FIVE
  OBLIGATIONS PASS at freeze time).

## CZ/MS idle-noise attribution

- **Action**: sensitivity rerun shows 30/3,000 failures with and without idle
  noise (LFR 0.0100 both arms); any idle-noise attribution withdrawn;
  hardware gap stated as model-attributed.
- **Artifacts**: manuscript §9 sensitivity summary, Discussion, conclusion.

## Related work / positioning (§10 repositioning)

- **Action**: `tab:priorart` (R1–R9) with per-row differentiation;
  "Closest prior art" paragraph naming Beverland et al. fail-fast as the
  strongest comparison (accelerated nominal rare-event estimation vs our
  adversarial worst-case bounds) and differentiating Pacenti et al.'s
  stochastic DEM failure structure.
- **Artifacts**: manuscript §2; Appendix D review-source list R1–R17.

## Known v24 limitations disclosed in the manuscript

- Λ second rung unresolvable at 20,000 trials/rung.
- symatch weight-1 diagnostic uses a fixed p_phys=0.001 prior; matched-prior
  variants deferred.
- REP3 routing proxy closed analytically (§6 item 8); twirling bridge
  analytic closure θ_L = −2θ³ + O(θ⁵) (item 6).
- C01 WS-C invalidation disclosure (above).
- WSC v24 grid regeneration in progress at freeze time; p=0.001 point
  complete and verified.
