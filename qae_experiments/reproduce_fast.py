"""Fast deterministic verification for the QAE V16 archive.
Runs only checks that do not require stochastic decoder backends or long Monte Carlo jobs.
"""
from __future__ import annotations
import subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent

def run(script: str, desc: str) -> None:
    print("\n" + "="*72)
    print(desc)
    print(script)
    t0 = time.time()
    r = subprocess.run([sys.executable, str(ROOT / script)], cwd=str(ROOT))
    print(f"elapsed={time.time()-t0:.1f}s exit={r.returncode}")
    if r.returncode:
        sys.exit(r.returncode)

print("QAE V16 fast reproducibility verification")
run("verify_certificate.py", "BB72 finite-instance certificate")
run("generate_minimax_bounds.py", "Analytic minimax lower-bound regeneration")
run("validate_seed_consistency.py", "Deterministic seed-policy validation")
run("validate_table_shapes.py", "CSV row-count and SHA-256-field validation")
run("verify_hashes.py", "SHA-256 archive-integrity verification")
print("\nFAST VERIFICATION PASSED")
