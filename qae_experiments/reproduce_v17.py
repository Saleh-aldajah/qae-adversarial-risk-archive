"""
reproduce_v17.py  —  Master reproduction script for the v17 revision archive.

Regenerates every manuscript-used table (v16 base tables + v17 extension
experiments E0-E6) and verifies archive integrity. Run from the archive root:

    cd /path/to/revision-archive
    python reproduce_v17.py

Measured wall-clock on the reference 3-core / 3 GB box (v17 audit run):
  v16 base tables ............ ~7-8 min (single-round 198 s, RC 207 s,
                               hardware 24 s, certificate ~4 s)
  E0 correctability .......... ~5 s
  E1 rare-event (6 x 10^6) ... ~37 min sequential (dominant cost)
  E2 UF-BFS BB288 ............ ~30 s
  E3 adaptive RC ............. ~70 min sequential worst case
                               (BB288 rows dominate; parallel per-code
                               processes cut this to ~55 min)
  E4 robustness .............. ~1 min
  E5 cross-check ............. ~10 s
  E6 BP-guided matching ...... ~1.5 min
  Figures F1-F7 .............. ~10 s
  TOTAL (sequential) ......... ~2 h; ~1 h with E1/E3 codes run in parallel
(B3 fix: v16's "2-4 hours" claim is corrected with these measured values.)

Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
import subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def run(script, desc, args=()):
    print(f"\n{'='*60}")
    print(f"STEP: {desc}")
    print(f"Script: {script} {' '.join(args)}")
    print('='*60, flush=True)
    t0 = time.time()
    r = subprocess.run([sys.executable, str(ROOT/script), *args],
                       cwd=str(ROOT), capture_output=False)
    elapsed = time.time() - t0
    status = "PASS" if r.returncode == 0 else f"FAIL (exit {r.returncode})"
    print(f"\n-> {status}  ({elapsed:.0f}s)", flush=True)
    if r.returncode != 0:
        print("ERROR: stopping reproduce_v17.py")
        sys.exit(1)
    return elapsed

print("QAE Reproducibility Suite - v17 (revision candidate)")
print("Regenerates every manuscript table from code.")
print("="*60)

# ── v16 base tables (unchanged protocols; byte-identical regeneration) ──
run("verify_certificate.py",
    "BB72 certificate: commutation, dimension, d>=6 MitM, t=2 exhaustive")
run("generate_minimax_bounds.py", "Minimax fidelity lower bounds (analytic)")
run("run_single_round_only.py",
    "Single-round BP+OSD + MWPM-DEM + UF-BFS (10k trials/row)")
run("run_rc_only.py", "Repeated-cycle BP+OSD (v16 budgets)")
run("run_hardware_ablations.py", "Hardware ablations + 3-backend comparison")

# ── v17 extension experiments ──
run("run_e0_correctability.py", "E0: per-weight correctability contrast")
run("run_e1_rare_event.py", "E1: rare-event BP+OSD (6 x 10^6 trials)")
run("run_e2_uf_bb288.py", "E2: UF-BFS BB288 (7 p x 10k)")
run("run_e3_rc_adaptive.py", "E3: adaptive repeated-cycle BB72", ("BB72",))
run("run_e3_rc_adaptive.py", "E3: adaptive repeated-cycle BB144", ("BB144",))
run("run_e3_rc_adaptive.py", "E3: adaptive repeated-cycle BB288", ("BB288",))
run("run_e4_robustness.py", "E4: decoder-hyperparameter robustness sweep")
run("run_e5_crosscheck.py", "E5: independent-path cross-check")
run("run_e6_bp_guided.py", "E6: BP-guided matching vs MWPM-DEM")

# ── figures ──
run("make_figures.py", "Figures F1-F7 (PDF + PNG)")

# ── validation ──
run("validate_seed_consistency.py", "Deterministic SHA-256 seed validation")
run("validate_table_shapes.py", "CSV row-count and hash-field validation")
run("verify_hashes.py", "SHA-256 manifest verification (inputs only)")

print("\n" + "="*60)
print("ALL STEPS COMPLETE - v17 archive is fully reproducible")
print("="*60)
