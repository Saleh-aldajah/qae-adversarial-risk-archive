"""
reproduce_all.py  —  Master reproduction script.

Regenerates every manuscript-used table and verifies archive integrity.
Run from the archive root directory:

    cd /path/to/archive
    python reproduce_all.py

Approximate total runtime: 2-4 hours (single-round 10k trials dominates).
Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
import subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def run(script, desc):
    print(f"\n{'='*60}")
    print(f"STEP: {desc}")
    print(f"Script: {script}")
    print('='*60)
    t0 = time.time()
    r = subprocess.run([sys.executable, str(ROOT/script)],
                       cwd=str(ROOT), capture_output=False)
    elapsed = time.time() - t0
    status = "PASS" if r.returncode == 0 else f"FAIL (exit {r.returncode})"
    print(f"\n→ {status}  ({elapsed:.0f}s)")
    if r.returncode != 0:
        print("ERROR: stopping reproduce_all.py")
        sys.exit(1)
    return elapsed

print("QAE Reproducibility Suite - v16")
print("Regenerates every manuscript table from code.")
print("="*60)

# Step 1: Certificate (fast, must pass first)
run("verify_certificate.py",
    "BB72 certificate: commutation, dimension, d>=6 MitM, t=2 exhaustive")

# Step 2: Analytic bounds (instant)
run("generate_minimax_bounds.py",
    "Minimax fidelity lower bounds (analytic, <1s)")

# Step 3: Single-round (slow, ~2h)
run("run_single_round_only.py",
    "Single-round BP+OSD + MWPM-DEM + UF-BFS (3 codes × 7 p × 2 decoders, 10k trials)")

# Step 4: Repeated-cycle (~1h)
run("run_rc_only.py",
    "Repeated-cycle BP+OSD (BB72 d=6, BB144 d=12, BB288 d=18)")

# Step 5: Hardware ablations (~10 min)
run("run_hardware_ablations.py",
    "Hardware ablation study (8 conditions + 3-backend comparison)")

# Step 6: Validate seeds and table shapes
run("validate_seed_consistency.py",
    "Deterministic SHA-256 seed-policy validation")
run("validate_table_shapes.py",
    "CSV row-count and SHA-256-field validation")

# Step 7: Verify final archive integrity
run("verify_hashes.py",
    "SHA-256 manifest verification (all primary files)")

print("\n" + "="*60)
print("ALL STEPS COMPLETE - archive is fully reproducible")
print("="*60)
