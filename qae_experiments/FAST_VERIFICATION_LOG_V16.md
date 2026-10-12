# QAE V16 Fast Verification Log

```text
BB72: n=72 k=12 rx=30 rz=30 commutation=PASS
  HX sha256: 7ab0973bfd02e399d69728d26e67dbfa...
  HZ sha256: 267f345c09710ec0cfad1e49e0786b26...
BB144: n=144 k=12 rx=66 rz=66 commutation=PASS
  HX sha256: 195d5586a406f0194b89649b6a2499ec...
  HZ sha256: 72dc3b9cefec7d45c99325c8f8d07871...
BB72 Certificate Verification  (self-contained, archive-local)
============================================================
O1  Commutation HX @ HZ^T = 0 (mod 2):  PASS
O2  Dimension k = 72 - 30 - 30 = 12: PASS
O3a SHA-256 matrix identity:             PASS
O3b d>=6 MitM (Z-comp): left=2,629, right=62,269, witnesses=0:  PASS
O3b d>=6 MitM (X-comp): left=2,629, right=62,269, witnesses=0:  PASS
O4  Radius-2 correctability (2,629 patterns):  PASS

Saved: bb72_certificate_report.json

============================================================
ALL FOUR OBLIGATIONS PASS
  d >= 6: confirmed (MitM, 5,258 left + 124,538 right patterns, 0 witnesses)
  t = 2:  confirmed (exhaustive, 2,629 weight-<=2 patterns, 0 failures)
  p=0.000: LB=0.900000
  p=0.001: LB=0.900000
  p=0.002: LB=0.900000
  p=0.003: LB=0.899997
  p=0.004: LB=0.899987
  p=0.005: LB=0.899955
  p=0.006: LB=0.899878
  p=0.007: LB=0.899723
  p=0.008: LB=0.899443
  p=0.009: LB=0.898982
  p=0.010: LB=0.898271
  p=0.015: LB=0.888199
  p=0.020: LB=0.860032
  p=0.025: LB=0.807481
  p=0.030: LB=0.731055
  p=0.040: LB=0.535054
  p=0.050: LB=0.340550
  p=0.060: LB=0.192454
  p=0.070: LB=0.098480
  p=0.080: LB=0.046355
  p=0.090: LB=0.020317
  p=0.100: LB=0.008370

Saved minimax_lower_bounds.csv  (22 rows)
data/single_round_bposd_mwpm_dem.csv: 28 rows checked, 0 mismatches
data/single_round_all_codes.csv: 42 rows checked, 0 mismatches
data/single_round_uf_decoder.csv: 14 rows checked, 0 mismatches
data/repeated_cycle_bposd.csv: 14 rows checked, 0 mismatches
data/repeated_cycle_bb288_bposd.csv: 7 rows checked, 0 mismatches
data/repeated_cycle_all_codes.csv: 21 rows checked, 0 mismatches
data/hardware_ablations.csv: 8 rows checked, 0 mismatches
data/hardware_three_condition_comparison.csv: 15 rows checked, 0 mismatches

All seed fields verified across 149 rows.
PASS: data/single_round_bposd_mwpm_dem.csv: 28 rows (expected 28)
PASS: data/single_round_all_codes.csv: 42 rows (expected 42)
PASS: data/single_round_uf_decoder.csv: 14 rows (expected 14)
PASS: data/repeated_cycle_bposd.csv: 14 rows (expected 14)
PASS: data/repeated_cycle_bb288_bposd.csv: 7 rows (expected 7)
PASS: data/repeated_cycle_all_codes.csv: 21 rows (expected 21)
PASS: data/hardware_ablations.csv: 8 rows (expected 8)
PASS: data/hardware_three_condition_comparison.csv: 15 rows (expected 15)
PASS: data/minimax_lower_bounds.csv: 22 rows (expected 22)
All table shape and hash-length checks passed.

42 files verified OK, 0 failures
All files verified - archive integrity confirmed
QAE V16 fast reproducibility verification

========================================================================
BB72 finite-instance certificate
verify_certificate.py
elapsed=2.2s exit=0

========================================================================
Analytic minimax lower-bound regeneration
generate_minimax_bounds.py
elapsed=2.2s exit=0

========================================================================
Deterministic seed-policy validation
validate_seed_consistency.py
elapsed=2.4s exit=0

========================================================================
CSV row-count and SHA-256-field validation
validate_table_shapes.py
elapsed=2.2s exit=0

========================================================================
SHA-256 archive-integrity verification
verify_hashes.py
elapsed=2.1s exit=0

FAST VERIFICATION PASSED
```

This is a deterministic fast-verification transcript. Full stochastic reproduction still requires the declared `ldpc==2.4.1` and `pymatching==2.4.0` environment or the supplied Dockerfile.
