# Certified Adversarial Risk Bounds for Quantum Error-Correcting Memories

Evidence and software archive for the manuscript *"Decoder Evaluation and
Adversarial-Risk Certification for Quantum Error-Correcting Memories"*
(current: `v17-manuscript/main2_refurbished.tex`, Springer Nature `sn-jnl`
format, 56 pp; earlier lineage `main_v20`–`main_v24` retained in
`v17-manuscript/`). The bundled emulator package in `qec-emulator/` is the
canonical experiment version, **QEC Emulator v2.0.0**.

The project reframes quantum-memory evaluation as a **certification
problem**: for a fixed implementation (code + schedule + decoder) and a
bounded-weight fault-injection adversary, the operational risk
λ_M(W) = max_{|F|≤W} Pr[logical failure | F] is reported as simultaneous
intervals [L_W, U_W] at joint ≥95% confidence — exact where enumeration is
complete (the t = 2 radius; the noiseless injection boundary), and honestly
U_W = 1, with the gap printed, where it is not.

## Headline artifacts

| Artifact | Path |
|---|---|
| Risk certificate (11 systems/budgets, K = 676 Bonferroni family) | `qae_experiments/data/risk_certificate_v24.csv` |
| Claim-to-artifact map (18 claims, self-validating) | `qae_experiments/data/claim_artifact_map_v25.csv` |
| BB[[72,12,6]] exact-distance certificate checker (334 lines) | `qae_experiments/verify_certificate.py` |
| Injection-boundary endpoint tables (true-residual classifier) | `qae_experiments/data/injection_boundary_decoders_v24.csv` |
| Device campaigns (IBM Quantum records, pinned protocols) | `theory_test/`, `theory_test_consol/` |
| Corrected circuit-level arm (C01 repair, protocol-invariance tests) | `comparator/wsc_circuit_point.py`, `comparator/wsc_verify.py` |
| Finite-size extension (measured curve crossings, 9 rungs) | `qae_experiments/data/repeated_cycle_fss_*.csv`, `qae_experiments/run_e3_rc_fss.py` |
| Causal hardware ablation (executed 2026-10-11, 160,000 shots, pre-registered) | `theory_test_causal/` |
| Manuscript + cover letter (Overleaf-ready) | `v17-manuscript/` |
| Second-round response ledger | `RESPONSE_TO_REVIEW_V25.md` |

## Reproduce

```bash
pip install -r qae_experiments/requirements.txt   # exact pins (= environment.yml)
cd qae_experiments
python reproduce_all.py --quick        # validators over shipped artifacts (minutes)
python reproduce_all.py                # full offline regeneration (hours)
python reproduce_all.py --skip-adaptive --skip-ibd   # skip the longest arms
```

With Docker (build context must be the archive root):

```bash
docker build -t qae-v25 .
docker run --rm qae-v25                # == reproduce_all.py --quick
```

Hardware campaigns are experimental **records**: they re-attain only by
re-running the pinned protocols on device
(`qae_experiments/run_hw_bb72_injection.py`, `IBM_RUN_INSTRUCTIONS.md`);
offline reproduction never submits jobs.

## Integrity machinery

- Archive-wide SHA-256 manifest: `sha256_manifest.json`
  (`qae_experiments/gen_manifest.py` / `verify_hashes.py`).
- Seed consistency across all seed families (651 rows):
  `qae_experiments/validate_seed_consistency.py`.
- Table-shape validation (47 artifacts):
  `qae_experiments/validate_table_shapes.py`.
- Dated pinning/amendment chronology: manuscript Appendix
  `app:chronology` (Table `tab:chronology`).
- Quarantined invalid artifacts (v23 reversed extraction; the 2026-09-25
  stale-rerun incident) are retained, labeled, and excluded from every active
  path: `comparator/legacy_quarantine/`.

## Status note (2026-09-27)

The corrected WS-C circuit-level grid regenerates rate by rate under a
checkpointed runner; the p = 0.001 point is complete and verified, and the
manuscript claims only completed points. Merged grid:
`comparator/results/wsc_circuit_v24.csv` via `comparator/merge_wsc_circuit_v25.py`.

## Status note (2026-10-12)

Two evidence layers added since the 2026-09-27 snapshot:

- **Finite-size extension (E3-FSS).** The repeated-cycle ladder is extended
  upward to p = 0.016–0.050 under the identical pinned protocol and an
  independent seed stream: `run_e3_rc_fss.py`,
  `data/repeated_cycle_fss_{bb72,bb144,bb288,hip_bb288}.csv`. The manuscript
  reports two successive, mutually consistent curve crossings bracketing
  (0.032, 0.040) — graded evidence, not a threshold estimate.
- **Causal ablation (campaign 3).** Pre-registered and executed 2026-10-11 on
  ibm_marrakesh (160,000 shots, 53 s QPU): `theory_test_causal/` with
  predictions (SHA-256-pinned before execution), circuits, counts, and
  `results/causal_verdict.json` (1/5 pre-registered tests passed; the
  tightening arm narrows the widest archived stochastic interval by 55%).

The manuscript's emulator pin is **QEC Emulator v2.0.0**, matching the source
bundled in `qec-emulator/` (earlier "v1.2.4" strings in retired drafts were
stale). The companion software repository
[`qec-emulator`](https://github.com/Saleh-aldajah/qec-emulator) tracks the
JOSS-lineage releases separately.
