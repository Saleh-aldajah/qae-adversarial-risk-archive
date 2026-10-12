# QAE v16 Reproducibility Guide

**Author:** Dr. Saleh H. AlDaajeh  
**ORCID:** 0000-0001-7810-9290  
**Reserved archive DOI:** https://doi.org/10.5281/zenodo.20574329

> The DOI is reserved/prepared for Zenodo deposition. Cite it as active only after the public Zenodo record resolves. Until then, this archive is the authoritative reproducibility package.

---

## 1. Software environment

The long stochastic runners require the declared decoder environment:

```bash
Python >= 3.9
numpy >= 1.24
ldpc == 2.4.1
pymatching == 2.4.0
```

Install with pip:

```bash
pip install -r requirements.txt
```

or create a Conda environment:

```bash
conda env create -f environment.yml
conda activate qae-v16
```

A Dockerfile is also included:

```bash
docker build -t qae-v16-reproduce .
docker run --rm qae-v16-reproduce python reproduce_fast.py
docker run --rm qae-v16-reproduce python reproduce_all.py
```

---

## 2. Fast deterministic verification

This verifies the archive without re-running the long Monte Carlo simulations:

```bash
python reproduce_fast.py
```

It runs:

1. `verify_certificate.py` — BB72 commutation, dimension, `d >= 6` MitM certificate, `t = 2` exhaustive correctability, and the O5 exact-distance obligation (`d = 6` exactly: exhaustive weight-6 enumeration exhibiting 84+84 nontrivial weight-6 logicals).
2. `generate_minimax_bounds.py` — analytic lower-bound regeneration.
3. `validate_seed_consistency.py` — confirms all archived seed columns match SHA-256 `stable_seed()` rules.
4. `validate_table_shapes.py` — confirms row counts and full SHA-256 matrix-hash fields.
5. `verify_hashes.py` — confirms archive file integrity.

Expected terminal ending:

```text
FAST VERIFICATION PASSED
```

---

## 3. Full code-to-table reproduction

Run the full suite only in the declared environment because it invokes `ldpc` and `pymatching`:

```bash
python reproduce_all.py
```

Approximate runtime: 3-4 hours.

The script performs:

1. BB72 certificate verification.
2. Analytic minimax lower-bound regeneration.
3. Single-round BP+OSD, MWPM-DEM, and UF-BFS simulations.
4. Repeated-cycle BP+OSD simulations for BB72/BB144/BB288.
5. Hardware noise-model ablation simulations.
6. Seed consistency validation.
7. Table-shape validation.
8. SHA-256 manifest verification.

Expected terminal ending:

```text
ALL STEPS COMPLETE - archive is fully reproducible
```

---

## 4. Individual commands

```bash
python verify_hashes.py
python verify_certificate.py
python generate_minimax_bounds.py
python validate_seed_consistency.py
python validate_table_shapes.py
python run_single_round_only.py
python run_rc_only.py
python run_hardware_ablations.py
```

Output files:

| Command | Main output |
|---|---|
| `verify_certificate.py` | `data/bb72_certificate_report.json` |
| `generate_minimax_bounds.py` | `data/minimax_lower_bounds.csv` |
| `run_single_round_only.py` | `data/single_round_bposd_mwpm_dem.csv`, `data/single_round_all_codes.csv`, `data/single_round_uf_decoder.csv` |
| `run_rc_only.py` | `data/repeated_cycle_bposd.csv`, `data/repeated_cycle_bb288_bposd.csv`, `data/repeated_cycle_all_codes.csv` |
| `run_hardware_ablations.py` | `data/hardware_ablations.csv`, `data/hardware_three_condition_comparison.csv` |

---

## 5. Deterministic seed policy

All current runners use SHA-256-derived seeds rather than Python's randomized built-in `hash()`:

```python
def stable_seed(*args):
    payload = "|".join(map(str, args)).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:4], "big")
```

`validate_seed_consistency.py` checks the archived seed columns against the exact formulas used by the runners.

---

## 6. Manifest policy

`sha256_manifest.json` is authoritative. Its tracked-file count is printed by:

```bash
python - <<'PY'
import json
print(len(json.load(open('sha256_manifest.json'))))
PY
```

The verifier must end with:

```text
0 failures
All files verified - archive integrity confirmed
```

`verify_hashes.py` exits with code 1 on any missing file or SHA-256 mismatch.

---

## 7. Scope notes for reviewers

- Hardware results are hardware noise-model simulations only. The archive does not include compiled circuits, routing schedules, calibration logs, or real-device execution data.
- MWPM-DEM and UF-BFS are graphified reference baselines. Their underperformance does not rule out correlated matching, auxiliary-detector constructions, hypergraph-aware decoders, or approximate maximum-likelihood methods.
- The repeated-cycle data are finite-size evidence, not an asymptotic threshold proof.
- The BB72 certificate establishes `d = 6` exactly: O3b excludes all nontrivial logicals of weight <= 5, and O5 (added in v21) enumerates all weight-6 kernel vectors exhaustively, exhibiting 84 + 84 nontrivial weight-6 logicals with verified anticommutation structure.


---

## 8. v21 additions (this version)

New data files, all generated with the pinned `stable_seed` policy and
carrying full `hx_sha256`/`hz_sha256` matrix digests:

| File | Content |
|---|---|
| `data/rare_event_bposd.csv` | E1 rare-event campaign: 6 rows x 1,000,000 trials (BB72/BB144/BB288 at p = 0.002, 0.004) |
| `data/repeated_cycle_adaptive_p010_bb72.csv` | E3 adaptive RC extension at p = 0.010 (d = 6 rounds, 4,000 trials) |
| `data/repeated_cycle_adaptive_p010_bb144.csv` | E3 adaptive RC extension at p = 0.010 (d = 12 rounds, 20,000 trials); resolves the fixed-grid BB144 non-monotone pair |
| `data/repeated_cycle_adaptive_p010_bb288.csv` | E3 adaptive RC extension at p = 0.010 (d = 18 rounds, 20,000 trials) |

New scripts:

- `run_e3_ext_p010.py` — derived from `run_e3_rc_adaptive.py`, protocol
  identical, restricted to the p = 0.010 grid point.
- `verify_e3_bb144_p012.py` — independent re-run of the archived
  BB144 p = 0.012 adaptive row (14/20,000 reproduced exactly).

`compute_lambda.py` (v22) regenerates `data/lambda_ladder.csv` (distance-ladder
suppression factors with log-method CIs) deterministically in under a second.

`verify_certificate.py` now verifies five obligations (O1-O5) and exits 0
only if the exact distance d = 6 certificate holds, including the pinned
weight-6 witness counts (120 kernel candidates and 84 nontrivial logicals
per sector) and anticommutation structure (2,592 pairs).

## 9. Hardware extension (v22, Extension 1)

`run_hw_bb72_injection.py` executes the Theorem-3 injection-budget game on
IBM Quantum Heron-r2 devices (QMAL-4 on hardware).  It is self-contained
and was validated offline on 2026-09-24:

- ideal selftest PASS (both extraction modes): all W<=2 probes 0
  failures; every O5-certified sharpness pair has a systematically
  failing half (Theorem 3(b));
- noisy rehearsal PASS (FakeKingston SPAM): pre-registered contrast
  W=0 ~1.3-1.6%, W=1 ~3.5-4.8%, W=2 ~4.7-13.0%, W=3 halves ~41-90%;
- routing audit: naive transpile gives ~2,400-2,800 CZ per extraction
  round on the 156-qubit heavy-hex map, so `--extraction rounds` is
  guarded pending a co-designed embedding; `--extraction singleshot`
  (default) has no two-qubit gates and fits one open-plan cycle.

Run instructions: `IBM_RUN_INSTRUCTIONS.md`.  The build sandbox cannot
reach `quantum.cloud.ibm.com` (Cloudflare IP block, verified
2026-09-24), so the hardware leg runs on the author's machine or Colab;
results return as `data/hw_bb72_injection*.csv/json` for integration.

## 10. v23 additions (calibrated limitation closures)

- `run_inj_boundary_decoders.py` -> `data/injection_boundary_decoders.csv`
  (126 rows): the Theorem-3 probe matrix replayed under BP+OSD,
  Union-Find, and BP-guided MWPM.  BP+OSD preserves the certified
  injection boundary (contrast >= 13x); UF and BP-guided MWPM collapse
  it (contrast 1.0x) --- decoder radius-completeness is
  security-relevant (Remark rem:crossdec).
- `run_twirling_residual.py` -> `data/twirling_residual.csv` (8 rows):
  exact REP3 logical channel under coherent axis noise; LFR twirl-exact
  (ratio 1.000), residual rotation cubic (~-2 theta^3), bridge ratio
  ~2/(3 theta) (Remark rem:twirl-num).

Both are deterministic and regenerate byte-identically:
`python run_inj_boundary_decoders.py` (~6 min) and
`python run_twirling_residual.py` (~10 min).
