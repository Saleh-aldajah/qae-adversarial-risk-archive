"""validate_table_shapes.py - minimal structural checks for manuscript-used CSVs."""
from __future__ import annotations
import csv, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
expected_rows = {
    "data/single_round_bposd_mwpm_dem.csv": 28,
    "data/single_round_all_codes.csv": 42,
    "data/single_round_uf_decoder.csv": 14,
    "data/repeated_cycle_bposd.csv": 14,
    "data/repeated_cycle_bb288_bposd.csv": 7,
    "data/repeated_cycle_all_codes.csv": 21,
    "data/hardware_ablations.csv": 8,
    "data/hardware_three_condition_comparison.csv": 15,
    "data/minimax_lower_bounds.csv": 22,
    # v17 extension experiments
    "data/correctability_by_weight.csv": 16,
    "data/rare_event_bposd.csv": 6,
    "data/single_round_uf_bb288.csv": 7,
    "data/repeated_cycle_adaptive_bb72.csv": 4,
    "data/repeated_cycle_adaptive_bb144.csv": 4,
    "data/repeated_cycle_adaptive_bb288.csv": 4,
    "data/robustness_sweep_bb72.csv": 18,
    "data/crosscheck_e5.csv": 6,
    "data/bp_guided_matching_bb72.csv": 6,
    # v21: p=0.010 adaptive extension (one row per code)
    "data/repeated_cycle_adaptive_p010_bb72.csv": 1,
    "data/repeated_cycle_adaptive_p010_bb144.csv": 1,
    "data/repeated_cycle_adaptive_p010_bb288.csv": 1,
    # v22: distance-ladder suppression factor
    "data/lambda_ladder.csv": 7,
    # v23: cross-decoder injection boundary + twirling residual
    "data/injection_boundary_decoders.csv": 126,
    "data/twirling_residual.csv": 8,
    # v24: corrected-estimand and extended-evidence artifacts
    "data/repeated_cycle_bposd_v24.csv": 14,
    "data/repeated_cycle_bb288_bposd_v24.csv": 7,
    "data/repeated_cycle_all_codes_v24.csv": 21,
    "data/repeated_cycle_adaptive_bb72_v24.csv": 4,
    "data/repeated_cycle_adaptive_bb144_v24.csv": 4,
    "data/repeated_cycle_adaptive_bb288_v24.csv": 4,
    "data/repeated_cycle_adaptive_p010_bb72_v24.csv": 1,
    "data/repeated_cycle_adaptive_p010_bb144_v24.csv": 1,
    "data/repeated_cycle_adaptive_p010_bb288_v24.csv": 1,
    "data/lambda_ladder_v24.csv": 15,
    "data/injection_boundary_decoders_v24.csv": 168,
    "data/injection_boundary_mcnemar_v24.csv": 252,
    "data/inj_radius_noiseless_v24.csv": 16,
    "data/twirling_residual_v24.csv": 8,
    "data/rep_exact_lfr_v24.csv": 30,
    "data/rep_exact_masks_v24.csv": 168,
    # v25: confidence-sequence adaptive ladder + risk-certificate artifact
    "data/rc_adaptive_cs_v24.csv": 15,
    "data/risk_certificate_v24.csv": 11,
    "data/claim_artifact_map_v25.csv": 18,
}
# v24 artifacts that gate the build but are produced by sibling pipelines
sibling_required = [
    "../comparator/results/wsc_circuit_v24.csv",
    "../comparator/results/wsc_verify_report.json",
    "../theory_test_consol/results/stoch_reanalysis_v24.csv",
    "../theory_test_consol/results/stoch_reanalysis_v24.json",
]
failures = 0
for rel, n in expected_rows.items():
    path = ROOT / rel
    with path.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    status = "PASS" if len(rows) == n else "FAIL"
    print(f"{status}: {rel}: {len(rows)} rows (expected {n})")
    if len(rows) != n:
        failures += 1
    for idx, row in enumerate(rows, 1):
        for col in ("hx_sha256", "hz_sha256"):
            if col in row and len(row[col]) != 64:
                print(f"FAIL: {rel}:{idx}: {col} length {len(row[col])}")
                failures += 1
for rel in sibling_required:
    path = ROOT / rel
    if path.exists():
        print(f"PASS: {rel}: present")
    else:
        print(f"FAIL: {rel}: missing (run the sibling pipeline first)")
        failures += 1
if failures:
    sys.exit(1)
print("All table shape and hash-length checks passed.")
