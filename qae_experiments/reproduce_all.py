#!/usr/bin/env python3
"""
QAE Reproducibility Suite - v24
================================
Master script to reproduce ALL v24 artifacts offline (no IBM Quantum calls).
Hardware protocols are separate: run_hw_bb72_injection.py and the ibm_demo/
pipeline require an IBM Quantum token and are never invoked here.

Usage:
    python reproduce_all.py                 # full regeneration + validation
    python reproduce_all.py --quick         # validate existing artifacts only
    python reproduce_all.py --skip-adaptive # skip the adaptive RC ladder (hours)

Environment:
    QAE_VENV_PY  interpreter with stim/ldpc/pymatching/relay_bp for heavy steps
                 (default: this environment's sys.executable)

v24 changes vs v16 (see reproduce_all_v16_legacy.py for the v16 suite):
  + injection-boundary v24 tables (decoders + noiseless exhaustive radius + McNemar)
  + REP exact stratification (Theorem: REP3 exact joint distribution)
  + twirling analytic closure (sec:twirling)
  + RC ladder on the v24 grids/seeds (run_rc_only_v24.py / run_e3_rc_adaptive_v24.py)
  + stochastic-comparison reanalysis under the v24 mask-conditioned estimand
    (withdraws the v23 'falsified' verdict)
  + WSC protocol-invariance tests (comparator/wsc_verify.py)
  + lambda ladder (per-BLOCK statistic; exact Clopper-Pearson ratio bounds)
  + v24 table-shape validation over the new CSV artifacts

v25 additions (second-round review):
  + RC adaptive uniform-mixture confidence sequences (gen_rc_adaptive_cs.py)
  + risk-certificate artifact: L_W/U_W per system under one K=676 Bonferroni
    family (gen_risk_certificate_v24.py)
  + injection endpoint classifier regression tests T1-T4 (true-residual
    semantics; IBD_TEST_ONLY=1 runs only the tests)
  + WSC circuit-point grid merge (comparator/merge_wsc_circuit_v25.py), when
    the per-point results are present
"""
import subprocess, sys, os, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
ARCHIVE = os.path.dirname(HERE)
PY = sys.executable
VENV = os.environ.get("QAE_VENV_PY", PY)


def run(name, script, use_venv=False, args=None, cwd=None, env=None):
    path = os.path.join(HERE, script)
    exe = VENV if use_venv else PY
    print(f"\n{'='*60}\n[STEP] {name}\n  -> {exe} {script} {' '.join(args or [])}\n{'='*60}")
    if not os.path.exists(path):
        print(f"  [FAIL] {script} not found")
        return False
    sub_env = dict(os.environ)
    if env:
        sub_env.update(env)
    r = subprocess.run([exe, path] + (args or []), cwd=cwd or os.path.dirname(path),
                       env=sub_env)
    print(f"  exit={r.returncode}")
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true",
                    help="skip slow regenerations, validate artifacts only")
    ap.add_argument("--skip-adaptive", action="store_true",
                    help="skip the adaptive RC ladder (hours)")
    ap.add_argument("--skip-ibd", action="store_true",
                    help="skip the injection-boundary regeneration (hours)")
    a = ap.parse_args()
    ok = True

    # ---- fast certificate / bound steps -------------------------------------
    ok &= run("O1-O5 certificate", "verify_certificate.py")
    ok &= run("Sion minimax bounds", "generate_minimax_bounds.py")

    # ---- heavy regenerations -------------------------------------------------
    if not a.quick:
        if not a.skip_ibd:
            ok &= run("Injection-boundary v24 (decoders + exhaustive radius + McNemar)",
                      "run_inj_boundary_decoders_v24.py", use_venv=True)
        ok &= run("REP exact stratification", "run_rep_exact_stratification.py",
                  use_venv=True)
        ok &= run("Twirling analytic closure", "run_twirling_analytic_v24.py",
                  use_venv=True)
        ok &= run("RC fixed grid (v24)", "run_rc_only_v24.py", use_venv=True)
        if not a.skip_adaptive:
            for code in ("bb72", "bb144", "bb288"):
                ok &= run(f"RC adaptive ladder v24 ({code})",
                          "run_e3_rc_adaptive_v24.py", use_venv=True, args=[code])
            for code in ("bb72", "bb144", "bb288"):
                ok &= run(f"RC adaptive ladder v24 p=0.010 ({code})",
                          "run_e3_rc_adaptive_v24_p010.py", use_venv=True,
                          args=[code])
        ok &= run("Stochastic reanalysis (v24 mask-conditioned estimand)",
                  "../theory_test_consol/run_stoch_reanalysis_v24.py", use_venv=True)
        ok &= run("WSC protocol-invariance tests (T1-T4)",
                  "../comparator/wsc_verify.py", use_venv=True)

    # ---- derivations + validators -------------------------------------------
    ok &= run("Lambda ladder (per-block, exact-CP ratio bounds)",
              "compute_lambda_v24.py")

    # v25 derivations (second-round review, gates G1-G2)
    ok &= run("RC adaptive confidence sequences (uniform-mixture, signed)",
              "gen_rc_adaptive_cs.py")
    ok &= run("Risk-certificate artifact (L_W/U_W per system)",
              "gen_risk_certificate_v24.py")
    ok &= run("Claim-to-artifact map (G4 manifest)",
              "gen_claim_map_v25.py")
    # Endpoint-classifier regression tests (T1-T4, true-residual semantics).
    # Fast: IBD_TEST_ONLY=1 exits right after the tests, before any trial.
    # The full injection rerun that regenerated the endpoint tables is the
    # heavy step above (run_inj_boundary_decoders_v24.py, ~7 min).
    ok &= run("Injection endpoint classifier regression tests (T1-T4)",
              "run_inj_boundary_decoders_v24.py", use_venv=True,
              env={"IBD_TEST_ONLY": "1"})

    ok &= run("Seed consistency", "validate_seed_consistency.py")
    ok &= run("Table shapes (incl. v24/v25 artifacts)", "validate_table_shapes.py")
    ok &= run("SHA256 hashes", "verify_hashes.py")

    print(f"\n{'='*60}\nRESULT: {'ALL PASS' if ok else 'FAILURES PRESENT'}\n{'='*60}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
