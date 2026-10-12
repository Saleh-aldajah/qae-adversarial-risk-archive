#!/usr/bin/env python
"""tt_common.py — shared machinery for the injection-budget hardware test.

Tests Theorem (spacetime-budget correctability + sharpness) and the
stochastic-injection bound on ibm_marrakesh repetition memories.

Arm design (both sectors X/Z; Z-sector injects X faults, X-sector Z faults):
  REP5 (d=5, t=2, R=4): base | w2 worst-case {2,3} | w3 worst-case {1,2,3}
                        | stochastic p in {0.01, 0.05, 0.10}
                        (50 variants x 200 shots each)
  REP3 (d=3, t=1, R=4): base | w1 worst-case {1}   | w2 worst-case {0,2}

Injection round r* = R//2 = 2: faults applied on data qubits immediately
after round r* barrier, before round r*+1. Layout: the metrology-selected
B-lines of the active-provenance campaign, FIXED across all arms so that
injection is the only varying factor.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DEMO = HERE.parent / "ibm_demo"
sys.path.insert(0, str(DEMO))

from ibm_demo_common import (BACKEND_NAME, OPT_LEVEL, TOKEN_PATH,  # noqa: E402
                             build_dem, canonical_circuit_digest,
                             counts_to_observables, dump_json, sha256_file,
                             stable_seed, wilson95)

ROUNDS = 4
INJ_ROUND = ROUNDS // 2          # inject after round-2 barrier (0-indexed)
SHOTS_DET = 10_000
STOCH_VARIANTS = 50
SHOTS_STOCH = 200
STOCH_PS = (0.01, 0.05, 0.10)
D_OF = {"REP3": 3, "REP5": 5}
T_OF = {"REP3": 1, "REP5": 2}
LINE = {"REP3": [2, 3, 4, 5, 6], "REP5": [2, 3, 4, 5, 6, 7, 8, 9, 10]}

# worst-case deterministic injections (data-qubit indices)
DET_INJ = {"REP3": {"w1": [("X", 1)], "w2": [("X", 0), ("X", 2)]},
           "REP5": {"w2": [("X", 2), ("X", 3)],
                    "w3": [("X", 1), ("X", 2), ("X", 3)]}}

CIRC = HERE / "circuits"
COUNTS = HERE / "counts"
RES = HERE / "results"
PRED = HERE / "predictions"
for p in (CIRC, COUNTS, RES, PRED):
    p.mkdir(exist_ok=True)


def build_rep_circuit_inj(d: int, basis: str, rounds: int, inject=None):
    """build_rep_circuit with fault injection.

    inject: dict {round_index: [(pauli_letter, data_index), ...]} applied
    immediately after that round's barrier (before the next round).
    """
    from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

    assert basis in ("Z", "X") and d >= 3 and rounds >= 1
    inject = inject or {}
    nq = 2 * d - 1
    qr = QuantumRegister(nq, "q")
    cr = ClassicalRegister(rounds * (d - 1) + d, "meas")
    qc = QuantumCircuit(qr, cr, name=f"rep{d}_{basis}_r{rounds}_inj")

    data = list(range(0, nq, 2))
    anc = list(range(1, nq, 2))

    def apply_injection(t):
        for pauli, j in inject.get(t, []):
            q = data[j]
            if basis == "X":
                # X-sector stores |+_L>; a physical Z is the logical-class
                # fault; realise Z injection as H-X-H so the fault is a
                # physical X gate (Heron native), basis-conjugated.
                qc.h(q)
                qc.x(q)
                qc.h(q)
            else:
                qc.x(q)
        if inject.get(t):
            qc.barrier()

    if basis == "X":
        qc.h(data)
    for t in range(rounds):
        if basis == "X":
            qc.h(anc)
        for c, a in enumerate(anc):
            if basis == "Z":
                qc.cx(data[c], a)
            else:
                qc.cx(a, data[c])
        for c, a in enumerate(anc):
            if basis == "Z":
                qc.cx(data[c + 1], a)
            else:
                qc.cx(a, data[c + 1])
        if basis == "X":
            qc.h(anc)
        for c, a in enumerate(anc):
            qc.measure(a, cr[t * (d - 1) + c])
        if t < rounds - 1:
            qc.reset(anc)
        qc.barrier()
        apply_injection(t)
    if basis == "X":
        qc.h(data)
    for j, q in enumerate(data):
        qc.measure(q, cr[rounds * (d - 1) + j])
    return qc


def stoch_mask(code: str, basis: str, p: float, variant: int):
    """Pinned Bernoulli injection mask over data qubits (deterministic)."""
    rng = np.random.default_rng(stable_seed("INJTT", code, basis, f"p{p}", variant))
    d = D_OF[code]
    return [j for j in range(d) if rng.random() < p]


def binom_tail(d: int, t: int, p: float) -> float:
    """Pr[Bin(d,p) >= t+1] — the stochastic-bound slack."""
    from math import comb
    return sum(comb(d, k) * p**k * (1 - p) ** (d - k) for k in range(t + 1, d + 1))


def arm_list():
    """Full arm table. Each arm: dict(code, basis, name, kind, inject, shots)."""
    arms = []
    for code in ("REP5", "REP3"):
        d = D_OF[code]
        for basis in ("Z", "X"):
            arms.append(dict(code=code, basis=basis, name="base", kind="det",
                             inject=None, shots=SHOTS_DET))
            for tag, faults in DET_INJ[code].items():
                arms.append(dict(code=code, basis=basis, name=tag, kind="det",
                                 inject={INJ_ROUND: list(faults)},
                                 shots=SHOTS_DET))
            if code == "REP5":
                for p in STOCH_PS:
                    for v in range(STOCH_VARIANTS):
                        mask = stoch_mask(code, basis, p, v)
                        inj = {INJ_ROUND: [("X", j) for j in mask]} if mask else None
                        arms.append(dict(code=code, basis=basis,
                                         name=f"p{p}_v{v:02d}", kind="stoch",
                                         p=p, variant=v, mask=mask,
                                         inject=inj, shots=SHOTS_STOCH))
    return arms


def pin_predictions():
    """Pre-registered predictions, computed BEFORE any submission.

    Decision rules (fixed ex ante):
      * base arm: sanity, LFR expected ~1e-3 (A/B campaign baseline).
      * correctable worst-case arms (REP5-w2, REP3-w1): BOUND HOLDS if
        LFR_arm <= LFR_base + TOL_DET (two-proportion context, 10k shots).
      * sharpness arms (REP5-w3, REP3-w2): SHARP if LFR_arm >= SHARP_MIN.
      * stochastic arms: BOUND HOLDS if LFR(p) <= d0_hi + tail + TOL_STOCH,
        with d0_hi the upper Wilson bound of the base arm.
    """
    TOL_DET, TOL_STOCH, SHARP_MIN = 0.005, 0.002, {"REP5": 0.90, "REP3": 0.85}
    preds = {"created_utc": None, "protocol": {
        "TOL_DET": TOL_DET, "TOL_STOCH": TOL_STOCH, "SHARP_MIN": SHARP_MIN,
        "rounds": ROUNDS, "injection_round": INJ_ROUND,
        "seed_formula": "stable_seed('INJTT', code, basis, arm/p, variant)",
        "layout": "active-provenance B-lines, fixed across arms",
        "tests": []}}
    for code in ("REP5", "REP3"):
        d, t = D_OF[code], T_OF[code]
        wc = [k for k in DET_INJ[code] if len(DET_INJ[code][k]) <= t]
        sh = [k for k in DET_INJ[code] if len(DET_INJ[code][k]) == t + 1]
        for basis in ("Z", "X"):
            for k in wc:
                preds["protocol"]["tests"].append({
                    "code": code, "basis": basis, "arm": k, "type": "bound",
                    "rule": f"LFR_{k} <= LFR_base + {TOL_DET}"})
            for k in sh:
                preds["protocol"]["tests"].append({
                    "code": code, "basis": basis, "arm": k, "type": "sharp",
                    "rule": f"LFR_{k} >= {SHARP_MIN[code]}"})
            if code == "REP5":
                for p in STOCH_PS:
                    tail = binom_tail(d, t, p)
                    preds["protocol"]["tests"].append({
                        "code": code, "basis": basis, "arm": f"p{p}",
                        "type": "stochastic", "binom_tail": tail,
                        "rule": f"LFR({p}) <= d0_hi + {tail:.3e} + {TOL_STOCH}"})
    return preds
