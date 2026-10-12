#!/usr/bin/env python
"""ca_common.py -- shared constants and builders for the causal
hardware-ablation campaign (campaign 3, "causal dose-response").

Campaign purpose: convert the simulation-only hardware ablations of the
manuscript into causal claims on real devices by varying
experimenter-controlled knobs:

  Arm D  decoherence dose-response: per-round idle delay D in
         {0, 1000, 2000, 4000} ns inserted uniformly on all qubits
         (experimenter-controlled cycle-time stretch).
  Arm P  placement ablation: 8 disjoint REP5 lines, top-4 and bottom-4
         by the pinned lambda_N rule from the campaign snapshot.
  Arm T  interval tightening: 4x-shot re-run of the stochastic cell
         with the widest archived Wilson half-width (selected by pinned
         rule from the archived consolidation CSV).

Discipline is identical to campaigns 1-2: snapshot -> pinned-rule
selection -> predictions JSON + SHA-256 pins BEFORE any QPU submission;
noiseless Aer validation of every deterministic arm; abort on failure.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "theory_test_consol"))
sys.path.insert(0, str(HERE.parent / "theory_test"))
sys.path.insert(0, str(HERE.parent))  # archive root: ibm_demo_common.py

from ct_common import (BACKEND_A, OPT_LEVEL, TOKEN_PATH, arm_list,  # noqa: E402
                       binom_tail, canonical_circuit_digest, dump_json,
                       lambda_N, longest_path, select_lines, sha256_file,
                       stable_seed, stoch_mask, verify_path, wilson95)
from tt_common import (ROUNDS, SHOTS_DET, STOCH_PS, build_rep_circuit_inj)  # noqa: E402

CAMPAIGN = "C"
BACKEND = BACKEND_A                      # ibm_marrakesh (continuity)

# Arm D: dose ladder in nanoseconds of added per-round idle delay
DOSES_NS = (0, 1000, 2000, 4000)
DOSE_BASIS = "Z"
DOSE_D = 5                               # REP5, the established workhorse

# Arm P: placement counts
N_PLACE_BEST = 4
N_PLACE_WORST = 4
PLACE_SHOTS = SHOTS_DET                  # 10_000 per placement

# Arm T: tightening multiplier over the archived SHOTS_STOCH (200)
TIGHTEN_MULT = 4
TIGHTEN_SHOTS = 200 * TIGHTEN_MULT       # 800 per variant

CIRC = HERE / "circuits"
PRED = HERE / "predictions"
RES = HERE / "results"
SNAP = HERE / "backend_snapshots"
for _d in (CIRC, PRED, RES, SNAP):
    _d.mkdir(exist_ok=True)

ARCHIVE_CONSOL_CSV = (HERE.parent / "theory_test_consol" / "results"
                      / "consol_results.csv")


def build_rep_circuit_dose(d: int, basis: str, rounds: int, delay_ns: float,
                           dt: float):
    """REP-d memory circuit with a uniform per-round idle delay.

    A delay of `delay_ns` (converted to dt, rounded) is applied to EVERY
    qubit immediately after each round's closing barrier for the first
    `rounds - 1` rounds.  delay 0 returns the unmodified campaign circuit.
    This is the experimenter-controlled decoherence dose: total added idle
    time per qubit = (rounds - 1) * delay_ns.
    """
    from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

    base = build_rep_circuit_inj(d, basis, rounds, inject=None)
    if delay_ns <= 0:
        return base
    delay_dt = int(round(delay_ns / dt))
    nq = 2 * d - 1
    qr = base.qregs[0]
    cr = base.cregs[0]
    qc = QuantumCircuit(qr, cr, name=f"rep{d}_{basis}_r{rounds}_dose{delay_ns:g}ns")
    data = list(range(0, nq, 2))
    anc = list(range(1, nq, 2))

    if basis == "X":
        qc.h(data)
    for t in range(rounds):
        if basis == "X":
            qc.h(anc)
        for c, a in enumerate(anc):
            qc.cx(data[c], a) if basis == "Z" else qc.cx(a, data[c])
        for c, a in enumerate(anc):
            qc.cx(data[c + 1], a) if basis == "Z" else qc.cx(a, data[c + 1])
        if basis == "X":
            qc.h(anc)
        for c, a in enumerate(anc):
            qc.measure(a, cr[t * (d - 1) + c])
        if t < rounds - 1:
            qc.reset(anc)
        qc.barrier()
        if t < rounds - 1:
            qc.delay(delay_dt, qr, unit="dt")
    if basis == "X":
        qc.h(data)
    for j, q in enumerate(data):
        qc.measure(q, cr[rounds * (d - 1) + j])
    return qc


def pick_tightening_cell(archive_csv):
    """Pinned rule: aggregate the archived consolidation stochastic rows by
    (code, basis, p), take the cell with the widest Wilson 95% interval on
    the pooled counts among cells with >= 1 failure.  Deterministic.
    Returns dict(code, basis, p, failures, shots, ci_lo, ci_hi)."""
    import csv
    agg = {}
    with open(archive_csv) as f:
        for r in csv.DictReader(f):
            if r.get("kind") != "stoch":
                continue
            k = (r["code"], r["basis"], float(r["p"]))
            f_, t_ = agg.get(k, (0, 0))
            agg[k] = (f_ + int(r["failures"]), t_ + int(r["shots"]))
    best = None
    for (code, basis, p), (f_, t_) in agg.items():
        if f_ < 1:
            continue
        lo, hi = wilson95(f_, t_)
        w = hi - lo
        key = (w, code, basis, p)
        if best is None or key > best[0]:
            best = (key, dict(code=code, basis=basis, p=p, failures=f_,
                              shots=t_, ci_lo=lo, ci_hi=hi))
    if best is None:
        raise RuntimeError("no eligible stochastic cell in archive CSV")
    return best[1]
