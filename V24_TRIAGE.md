# V24 Triage Map — claim disposition after the v23 scientific review

Phase 1 of the review's Section 14 plan: v23 is frozen as the reviewed record
(delivered zips + SHA256SUMS_v23.txt, unmodified). Every central claim is
classified below as RETAINED / CORRECTED / WITHDRAWN / RERUN, with the v24
action and artifact. Review finding IDs (C01–C11) and section numbers refer
to `QAE_v23_Scientific_Review_and_Improvement_Plan.docx`.

## Validity findings (Sec. 3)

| Finding | Claim | Disposition | v24 action / artifact |
|---|---|---|---|
| C01 | Circuit-level graphification penalty (WSC arm) | WITHDRAWN (invalid circuit) + RERUN | CNOT directions corrected in `comparator/wsc_circuit_point.py` (circuit_rev `v24-corrected-extraction`); independent deterministic verification `comparator/wsc_verify.py` (T1 gadget parity incl. bug signature, T2 codespace invariants, T3 all-72-column injection match, T4 detector/observable audit — ALL PASS); v23 CSV renamed `wsc_circuit_v23_reversed_extraction_INVALID.csv` + `WSC_V23_INVALID.md`; full 7-point grid rerun (20k shots x 5 decoders) -> `results/wsc_circuit.csv` |
| C02 | prop:bridge max-sector inequality | WITHDRAWN (false as stated) + CORRECTED | Replace with either-sector block-failure bound: diamond distance 2(1-p_I) <= 2*(LFR_X + LFR_Z); sharp sector relation LFR_Z = p_X + p_Y etc.; counterexample (p_X=p_Z=0.1, p_I=0.8) acknowledged; ACE-gap arithmetic fixed (0.1880); equilibrium-gap claim removed |
| C03 | Fixed-mask stochastic falsification of naive bound | WITHDRAWN as falsification; RETAINED as discovery | `theory_test_consol/run_stoch_reanalysis_v24.py`: mask-conditioned thresholds reproduce reviewer's numbers exactly (0.022384/0.042729/0.022384/0.042566); no cell exceeds -> `results/stoch_reanalysis_v24.{csv,json}`; composed Binomial x Poisson model relabeled discovery (chronology disclosed) |
| C04 | cor:inj-cert "sound and complete certification" | WITHDRAWN | Replaced by three honest outputs: (i) worst-case certificate over enumerated space with coverage argument; (ii) model-conditional bound; (iii) challenge test restricted to the tested set, with explicit coverage gap; honest U_W = 1 where unexplored |
| C05 | Repetition theorem for arbitrary Pauli | CORRECTED (scope) | Restricted to the protected CSS sector; per-theorem scope statements added (classical observable / one sector / full channel); counterexample (single Z = logical phase) acknowledged |
| C06 | Calibration tails certified | CORRECTED | Relabeled model predictions (gate/idle omitted; Poisson tail not conservative); lambda_N formula and omission disclosed |
| C07 | Endpoint (failure = non-benign residual) | CORRECTED | Four-category endpoint everywhere (valid_correct / valid_wrong_logical / invalid_residual / abort); UF-BFS 2,332 failures reclassified as decoder failure (nonzero residual syndrome); implemented in `run_inj_boundary_decoders_v24.py` and published per-trial (`ibd_v24_trial_categories.npz`) |
| C08 | One-command reproduction | CORRECTED | reproduce_all extended to current extensions; ibm_demo_common vendored; offline vs hardware paths separated; validators updated (see Sec. 12 work items) |
| C09 | Decoder equivalence (symatch) | CORRECTED | Conclusions limited to tested construction; prespecified equivalence margins; matched-prior control; bare-symatch count discrepancy resolved/ disclosed |
| C10 | Bibliography | CORRECTED | Sahay-Williamson-Brown authorship; Maurer FPGA first author; defective-components attribution (Drouet et al.); Pacenti given names removed; Lewis-Soudjani-Zuliani verification review; IBM arXiv id fixed; emulator DOI fixed; "gross code" = BB144 |
| C11 | QMAL assurance ladder | WITHDRAWN + REPLACED | Scoped evidence profile binding (code, circuit, decoder, noise envelope, adversary, calibration interval, confidence); QMAL-5 two-device claim removed (placement only on marrakesh) |

## Mathematical repairs (Sec. 4)

- 4.1 minimax: fixed-implementation adversarial risk lambda(W) = max_{A in W} q(F)
  restated as the central definition; minimax/Knill-Laflamme demoted to background.
- 4.4 composition: Bin(d,p) -> Bin(n_d,p) correction; Pauli/binary composition is
  not set union; "refutes whenever pi(1)>0" removed.
- 4.6 syndrome insufficiency: clean {E, E*L} non-identifiability pair with explicit
  budget condition; work-factor corollary gains hypotheses (deterministic
  tie-breaking, radius completeness, attack knowledge, failure threshold).
- 4.7 twirling: analytic diamond closures 2|g| and 2*sqrt(p_L^2+g^2) added with
  derivation (`run_twirling_analytic_v24.py` -> `twirling_residual_v24.csv`);
  archived variational numbers confirmed equal to exact values up to archived
  rounding; Huang-Doherty-Flammia [R8] cited.
- 4.8 counting lemma: delimited (BB rates 1/6, 1/12, 1/24 vs surface 1/6; no
  asymptotic or matched-rate claim).

## Circuit / evidence repairs (Sec. 5-7)

- 5.3 injection boundary: rebuilt as `run_inj_boundary_decoders_v24.py` —
  frozen probe set (single seed, `ibd_v24_freeze.json`), identical native
  errors replayed to all decoders, noiseless exhaustive radius test separated
  (Phase A: w<=2 exhaustive 2,629 masks/side + 20,008 weight-3 sample),
  four-category endpoint, MW-lookup radius-complete reference decoder,
  exact McNemar paired contrasts (252 rows). Headline: BP+OSD preserves the
  certified boundary (W<=2 max wrong-logical 0.0016-0.0196 vs certified halves
  pair-max 0.73-0.87); UF / BP-guided MWPM either commit wrong-logical
  corrections on weight-2 faults noiselessly (13 and 3 of 2,629) or abstain
  into invalid corrections under syndrome noise (44-58% invalid_residual on
  the W<=2 control set; 71-98% at weight 2).
- 5.4 RC priors: aligned exactly (final-round fault variables removed from the
  decoded model, not epsilon-floored) in `run_rc_only_v24.py` /
  `run_e3_rc_adaptive_v24.py`; all Lambda/distance-ladder conclusions recomputed
  from `*_v24.csv` only.
- 5.5 certificates: O4 sectorwise-vs-mixed-Pauli explanation; separate trusted
  checker; published logical basis / witness schema; syndrome-consistency
  assertions in decoders.
- 6.4: calibration tails = model predictions (see C06).
- 6.5: placement A/B downgraded to pilot observation (normal one-sided p~0.042,
  exact stratified ~0.0517; method-sensitive, exploratory).
- 6.6: exact zero-failure upper bound 2.996/N identified alongside Wilson
  2.71/N; confidence sequences (Howard et al. [R12]) referenced for sequential
  allocation; joint risk-ratio construction.
- 7: Kunlun described as reanalysis of a released DEM (not raw shots); Lambda as
  cube-root of block-failure ratio, not per-cycle suppression; "matched
  protocol" claim vs surface-code hardware [R9] removed; CZ/MS idle-noise
  conclusion removed (30/3000 both arms — unsupported).

## Security / originality / structure (Sec. 8-11, 13)

- 8: formal threat model (protected asset, trust boundary, attacker
  capabilities); QEC != quantum authentication [R10, R11]; SHA-256 manifests =
  integrity vs trusted reference, not authentication.
- 9: closest-prior-art table R1-R9 with Fail-fast [R5] as strongest comparison
  and substantive Pacenti [R6] differentiation.
- 10: repositioning — primary question = certified adversarial risk bounds
  lambda(W) = [L_W, U_W] with simultaneous (Bonferroni) intervals and honest
  U_W = 1 on unexplored regions; four-part contribution restated.
- 11.1: verified reference model progression (repetition -> small CSS -> BB72).
- 11.2: exact small-code stratification implemented
  (`run_rep_exact_stratification.py`: REP3/5/7 = 8/32/128 masks measured
  exhaustively, circuit == analytic on all 168 masks, exact Binomial-weighted
  LFR curves, zero mask-sampling variance).
- 13 corrections: 32.2x paired-grid ratio; 0.1880 ACE gap; idle-conclusion
  fix; suppression-comparison caveat; statistical language (detectable
  differences, prespecified equivalence); preregistration chronology;
  prop:syndrome-insufficiency label fixed; claim map -> multipage longtable.

## New evidence generated for v24 (all offline, seeded, archived)

| Artifact | Rows | Content |
|---|---|---|
| `comparator/results/wsc_verify_report.json` | 4 tests | Independent circuit verification, ALL PASS |
| `comparator/results/wsc_circuit.csv` | 35 | Corrected circuit-level grid (rerun) |
| `qae_experiments/data/inj_radius_noiseless_v24.csv` | 16 | Phase A noiseless radius, 4 decoders x 2 sides |
| `qae_experiments/data/injection_boundary_decoders_v24.csv` | 168 | Phase B frozen paired noisy injection |
| `qae_experiments/data/injection_boundary_mcnemar_v24.csv` | 252 | Exact paired contrasts |
| `qae_experiments/data/ibd_v24_trial_categories.npz` | 272k trials x 4 | Per-trial category codes (auditable) |
| `qae_experiments/data/rep_exact_masks_v24.csv` | 168 | Exact per-mask responses REP3/5/7 |
| `qae_experiments/data/rep_exact_lfr_v24.csv` | 30 | Exact Binomial-weighted LFR(p) |
| `qae_experiments/data/twirling_residual_v24.csv` | 8 | Analytic diamond closures + archived comparison |
| `qae_experiments/data/repeated_cycle_*_v24.csv` | 21 + 12 | Prior-aligned RC grid + adaptive ladder |
| `theory_test_consol/results/stoch_reanalysis_v24.csv` | 12 | Mask-conditioned stochastic reanalysis |

*Author: Saleh H. AlDaajeh (ORCID 0000-0001-7810-9290). Generated during the
v24 reconstruction; see PATCH_NOTES_V24.md for the chronological log.*
