#!/usr/bin/env python3
"""run_reset_sensitivity.py — P1-11 closure: ancilla-reset (preparation)
sensitivity Monte-Carlo for BB72 single-cycle, circuit-level model.

Question (referee P1-11): imperfect reset / ancilla thermalization is an
unexamined alternative to idle-window decoherence with identical
detection-rate scaling. This script ablates the preparation channel
(p_prep_ratio) against readout (p_meas_ratio) and idle (p_idle_ratio)
in the Pauli-propagating CircuitLevelModel, BB72, p=5e-4, 3,000 trials
per condition, radius-2 lookup decoder (identical to the hardware
ablation protocol). Seeds pinned via stable_seed('RESET', ...).

Output: reset_sensitivity.csv + stdout table.
"""
import sys, csv, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "qec-emulator"))
sys.path.insert(0, str(HERE.parent / "v17-rerun"))

from bb_codes import BB72, syn_from_mask, gf2_rref, in_rowspace
from decoders import arr_to_mask, bernoulli_mask
from qae_utils import stable_seed, wilson95, build_lookup
from qec_emulator.noise import CircuitLevelModel, syndrome_from_mask
from qec_emulator.codes import BB72 as BB72Emu

code = BB72
n, n2 = code['n'], code['n'] // 2
HX_rref, HX_pivots = gf2_rref(code['HX'])
HZ_rref, HZ_pivots = gf2_rref(code['HZ'])
lz = build_lookup(code['hx_cols'], n, 2)
lx = build_lookup(code['hz_cols'], n, 2)

# convention cross-check: emulator syndrome == v17-rerun syndrome
cemu = BB72Emu()
rng = np.random.default_rng(12345)
for _ in range(50):
    m = int(rng.integers(0, 2**63)) | (int(rng.integers(0, 2**9)) << 63)
    assert syn_from_mask(m, code['hx_cols']) == syndrome_from_mask(m, cemu.hx_cols)
print("[check] syndrome conventions identical (50 random masks)")

def decode_success(ez, ex, sz, sx):
    cz = lz.get(sz, 0); cx = lx.get(sx, 0)
    rz = ez ^ cz; rx = ex ^ cx
    vz = np.array([(rz >> i) & 1 for i in range(n)], dtype=np.uint8)
    vx = np.array([(rx >> i) & 1 for i in range(n)], dtype=np.uint8)
    return (in_rowspace(vz, HZ_rref, HZ_pivots) and
            in_rowspace(vx, HX_rref, HX_pivots))

P_BASE, T = 5e-4, 3000
CONDITIONS = [
    ("circuit: full model",      dict(p_prep_ratio=1.0, p_meas_ratio=1.0, p_idle_ratio=0.05)),
    ("circuit: no reset noise",  dict(p_prep_ratio=0.0, p_meas_ratio=1.0, p_idle_ratio=0.05)),
    ("circuit: reset x2",        dict(p_prep_ratio=2.0, p_meas_ratio=1.0, p_idle_ratio=0.05)),
    ("circuit: no readout",      dict(p_prep_ratio=1.0, p_meas_ratio=0.0, p_idle_ratio=0.05)),
    ("circuit: reset-only syn",  dict(p_prep_ratio=1.0, p_meas_ratio=0.0, p_idle_ratio=0.0)),
    ("circuit: readout-only syn",dict(p_prep_ratio=0.0, p_meas_ratio=1.0, p_idle_ratio=0.0)),
]

rows = []
print(f"BB72 circuit-level reset sensitivity, p={P_BASE}, {T} trials/condition")
for label, kw in CONDITIONS:
    model = CircuitLevelModel(**kw)
    seed = stable_seed("RESET", label, P_BASE)
    rng = np.random.default_rng(seed)
    failures = 0; t0 = time.time()
    for _ in range(T):
        z_mask, x_mask, syn_z, syn_x = model(cemu, P_BASE, rng)
        if not decode_success(z_mask, x_mask, syn_z, syn_x):
            failures += 1
    lo, hi = wilson95(failures, T)
    rows.append(dict(condition=label, p_base=P_BASE, trials=T, failures=failures,
                     lfr=round(failures / T, 6), ci_lo=round(lo, 6), ci_hi=round(hi, 6),
                     seed=seed, **{k: v for k, v in kw.items()},
                     note="P1-11 reset-sensitivity; simulation-model only"))
    print(f"  {label:<28} {failures:4d}/{T}  LFR={failures/T:.5f}  [{lo:.5f},{hi:.5f}]  ({time.time()-t0:.0f}s)")

with open(HERE / "reset_sensitivity.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print("[written] reset_sensitivity.csv")
