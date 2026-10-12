"""Shared utilities for the IBM Quantum pipeline-validation demo.

Provenance conventions mirror the v17 revision archive
(/mnt/agents/output/qec-work/revision-archive/README_DATASET.md):
  * deterministic seeds: int.from_bytes(SHA256(context)[0:4], 'big')
    (stable_seed / wilson95 copied verbatim from qae_utils.py, MIT);
  * SHA-256 digests bind every artifact to the manifest;
  * Wilson 95% intervals (z = 1.96) for rate estimates.

Seed formula #14 (SEED_NOTE.md):
    stable_seed('IBM', code, basis, rounds, decoder)
    -> seed_transpiler for the pinned transpile of each demo circuit.
Seed formula #15 (SEED_NOTE.md):
    stable_seed('IBMSIM', code, basis, rounds, decoder)
    -> seed_simulator for the offline Aer validation shots.

This is a PIPELINE validation (provenance scheme on live cloud jobs),
explicitly not a performance claim.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.sparse import csc_matrix, lil_matrix

# --------------------------------------------------------------------------
# Copied verbatim from revision-archive/qae_utils.py (MIT) — keep in sync.
# --------------------------------------------------------------------------


def stable_seed(*args):
    """Deterministic 32-bit seed: first 4 bytes of SHA-256 of the
    '|'-joined context string, big-endian. PYTHONHASHSEED-independent."""
    key = "|".join(str(a) for a in args).encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:4], 'big')


def wilson95(k, n):
    """Two-sided Wilson score interval, z = 1.96 (95%)."""
    if n == 0:
        return 0., 1.
    z = 1.96
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0., c - m), min(1., c + m)


# --------------------------------------------------------------------------
# Demo constants
# --------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
TOKEN_PATH = Path("/mnt/agents/upload/ibm_token.json")  # ONLY token handoff
BACKEND_NAME = "ibm_marrakesh"         # Heron r2, 156 qubits, Open Plan (was ibm_kingston: queue 405 vs 10 pending, same class; snapshot records the change)
DECODER_TAG = "MWPM-DEM"
OPT_LEVEL = 1                          # pinned transpile optimization level
SHOTS_ONLINE = 2000
SHOTS_OFFLINE = 2000
CONFIGS = [(d, basis, r)
           for d in (3, 5)
           for basis in ("Z", "X")
           for r in (1, 2, 4)]        # 12 configs

# Offline noise regime (documented Heron-class stand-in, NOT a calibrated
# model of ibm_kingston — the real calibration is snapshotted by 01):
NOISE = {
    "t1_us": 150.0,       # relaxation time
    "t2_us": 120.0,       # dephasing time (< 2*T1)
    "t_1q_ns": 60.0,      # sx/x gate duration
    "t_2q_ns": 660.0,     # cz gate duration (Heron-class)
    "p_2q": 3.0e-3,       # two-qubit depolarizing error
    "p_readout": 2.0e-2,  # assignment error
    "p_reset": 2.0e-3,    # reset error
}

# DEM edge weights (approximate, documented in SEED_NOTE.md/REPORT):
# space-like (data-qubit error per round): each data qubit sees <=2 CNOTs
# per round -> ~2*p_2q; time-like (ancilla readout): p_readout.
P_SPACE = 2.0 * NOISE["p_2q"]          # 6.0e-3
P_MEAS = NOISE["p_readout"]            # 2.0e-2


def seed14(code, basis, rounds, decoder=DECODER_TAG):
    """Formula #14: transpiler seed for a demo circuit."""
    return stable_seed("IBM", code, basis, rounds, decoder)


def seed15(code, basis, rounds, decoder=DECODER_TAG):
    """Formula #15: simulator seed for offline validation shots."""
    return stable_seed("IBMSIM", code, basis, rounds, decoder)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_circuit_digest(qc) -> str:
    """SHA-256 over the canonical op sequence (gate name, qubit indices,
    clbit indices, params). Deterministic across processes for a fixed
    seed_transpiler — unlike QPY bytes, whose serialized layout-register
    naming is nondeterministic in Qiskit 2.x (circuits remain ==-equal;
    see IBM_DEMO_REPORT.md §Reproducibility)."""
    lines = []
    for ins in qc.data:
        qi = [qc.find_bit(q).index for q in ins.qubits]
        ci = [qc.find_bit(c).index for c in ins.clbits]
        params = [str(p) for p in ins.operation.params]
        lines.append(f"{ins.operation.name}|{qi}|{ci}|{params}")
    return sha256_bytes("\n".join(lines).encode())


def dump_json(path, obj) -> str:
    """Canonical JSON dump (sorted keys, LF); returns sha256 of the bytes."""
    b = (json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n").encode()
    Path(path).write_bytes(b)
    return sha256_bytes(b)


# --------------------------------------------------------------------------
# Repetition-code memory circuits
# --------------------------------------------------------------------------

def code_tag(d: int) -> str:
    return f"REP{d}"


def build_rep_circuit(d: int, basis: str, rounds: int):
    """Repetition-code quantum-memory circuit.

    Layout (logical): data qubits 0..d-1, ancillas d..2d-2, ancilla c sits
    between data qubits c and c+1, so the required connectivity is a simple
    LINE:  data0 - anc0 - data1 - anc1 - ... - data(d-1)   (2d-1 qubits).

    basis 'Z': measure ZZ stabilizers, prepare/verify logical |0_L>.
    basis 'X': measure XX stabilizers, prepare/verify logical |+_L>.

    Classical register 'meas' (size rounds*(d-1)+d):
      clbit t*(d-1)+c          = ancilla c measurement, round t (t<rounds)
      clbit rounds*(d-1)+j     = final data-qubit j readout
    """
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

    assert basis in ("Z", "X") and d >= 3 and rounds >= 1
    nq = 2 * d - 1
    qr = QuantumRegister(nq, "q")
    cr = ClassicalRegister(rounds * (d - 1) + d, "meas")
    qc = QuantumCircuit(qr, cr, name=f"rep{d}_{basis}_r{rounds}")

    data = list(range(0, nq, 2))       # data qubit j -> qr[2j]
    anc = list(range(1, nq, 2))        # ancilla c   -> qr[2c+1]

    if basis == "X":
        qc.h(data)
    for t in range(rounds):
        if basis == "X":
            qc.h(anc)
        # layer 1: ancilla c couples to data c
        for c, a in enumerate(anc):
            if basis == "Z":
                qc.cx(data[c], a)
            else:
                qc.cx(a, data[c])
        # layer 2: ancilla c couples to data c+1
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
    if basis == "X":
        qc.h(data)
    for j, q in enumerate(data):
        qc.measure(q, cr[rounds * (d - 1) + j])
    return qc


def find_line_layout(coupling_map, n: int) -> list[int]:
    """Find a simple path of n device qubits (BFS over the coupling map)."""
    # undirected adjacency
    adj = {u: set() for u in coupling_map.physical_qubits}
    for u, v in coupling_map.get_edges():
        adj[u].add(v)
        adj[v].add(u)
    for start in sorted(adj):
        # DFS for simple path of length n (n <= 9 here, graph small)
        stack = [(start, [start])]
        while stack:
            node, path = stack.pop()
            if len(path) == n:
                return path
            for nb in sorted(adj[node], reverse=True):
                if nb not in path:
                    stack.append((nb, path + [nb]))
    raise RuntimeError(f"no line of {n} qubits found in coupling map")


# --------------------------------------------------------------------------
# Offline Heron-class stand-in backend + noise model
# --------------------------------------------------------------------------

HEAVY_HEX_DISTANCE = 7   # 115-qubit heavy-hex stand-in (Heron-class layout)
BASIS_GATES = ["rz", "sx", "x", "cz", "id", "reset", "measure", "delay"]


def offline_coupling_map():
    """Heavy-hex(7), 115 qubits — connectivity-class stand-in for the
    156-qubit Heron r2 lattice (NOT ibm_kingston's actual map; the real map
    is snapshotted by 01_snapshot_backend.py for the online run)."""
    from qiskit.transpiler import CouplingMap
    return CouplingMap.from_heavy_hex(HEAVY_HEX_DISTANCE)


def heron_noise_model():
    """Aer NoiseModel with the documented Heron-class parameters (NOISE):
    thermal relaxation on 1Q/2Q gates + depolarizing 2Q floor, assignment
    readout error, reset error. Idle noise during measurements is NOT
    modelled (documented simplification)."""
    from qiskit_aer.noise import (NoiseModel, ReadoutError,
                                  depolarizing_error, thermal_relaxation_error)
    p = NOISE
    t1, t2 = p["t1_us"] * 1e3, p["t2_us"] * 1e3   # ns
    nm = NoiseModel(basis_gates=["cz", "id", "rz", "sx", "x", "reset", "measure"])
    e1 = thermal_relaxation_error(t1, t2, p["t_1q_ns"])
    e2 = thermal_relaxation_error(t1, t2, p["t_2q_ns"]).tensor(
        thermal_relaxation_error(t1, t2, p["t_2q_ns"]))
    e2 = e2.compose(depolarizing_error(p["p_2q"], 2))
    nm.add_all_qubit_quantum_error(e1, ["sx", "x", "rz", "id"])
    nm.add_all_qubit_quantum_error(e2, ["cz"])
    nm.add_all_qubit_quantum_error(depolarizing_error(p["p_reset"], 1), ["reset"])
    nm.add_all_qubit_readout_error(
        ReadoutError([[1 - p["p_readout"], p["p_readout"]],
                      [p["p_readout"], 1 - p["p_readout"]]]))
    return nm


# --------------------------------------------------------------------------
# Detector error model (DEM) for the repetition memory experiment
# --------------------------------------------------------------------------

def check_matrix_rep(d: int) -> np.ndarray:
    """(d-1) x d parity-check matrix of the length-d repetition code."""
    H = np.zeros((d - 1, d), dtype=np.uint8)
    for c in range(d - 1):
        H[c, c] = 1
        H[c, c + 1] = 1
    return H


def build_dem(d: int, rounds: int, p_space: float = P_SPACE,
              p_meas: float = P_MEAS):
    """Fault-mechanism check matrix for PyMatching.

    Detectors: slices t = 0..rounds (t<rounds from ancilla differences,
    t = rounds from the final data readout), c = 0..d-2;
    index idx(t, c) = t*(d-1)+c.  Total D = (rounds+1)*(d-1).

    Faults:
      * data-qubit bit-flip edges at every slice t=0..rounds for each data
        qubit j: flip detectors idx(t,j-1), idx(t,j) (boundary edges flip
        one detector); EVERY data edge flips the logical observable (the
        final logical readout is the parity of the data bits).
      * time-like measurement edges between idx(t,c) and idx(t+1,c),
        t=0..rounds-1 (ancilla readout error); never flip the observable.

    Returns (H csc_matrix D x F, weights array F, faults array F).
    """
    D = (rounds + 1) * (d - 1)
    cols, weights, faults = [], [], []

    def idx(t, c):
        return t * (d - 1) + c

    for t in range(rounds + 1):
        for j in range(d):
            rows = []
            if j > 0:
                rows.append(idx(t, j - 1))
            if j < d - 1:
                rows.append(idx(t, j))
            cols.append(rows)
            weights.append(p_space)
            faults.append(1)
    for t in range(rounds):
        for c in range(d - 1):
            cols.append([idx(t, c), idx(t + 1, c)])
            weights.append(p_meas)
            faults.append(0)

    F = len(cols)
    H = lil_matrix((D, F), dtype=np.uint8)
    for f, rows in enumerate(cols):
        for r in rows:
            H[r, f] = 1
    w = np.array([math.log((1 - p) / p) for p in weights], dtype=float)
    return csc_matrix(H), w, np.array(faults, dtype=np.uint8)


def counts_to_observables(counts: dict, d: int, rounds: int):
    """Parse Sampler counts -> per-shot (syndrome vector, logical parity).

    Bit ordering: qiskit count strings are little-endian in the classical
    register — the rightmost character is clbit 0.
    """
    D = (rounds + 1) * (d - 1)
    ncb = rounds * (d - 1) + d
    syndromes, logicals, mult = [], [], []
    for key, n in counts.items():
        bits = key.replace(" ", "")
        assert len(bits) == ncb, f"unexpected count key {key!r}"
        b = [int(ch) for ch in reversed(bits)]   # b[i] = clbit i
        anc = [b[t * (d - 1) + c] for t in range(rounds) for c in range(d - 1)]
        dat = b[rounds * (d - 1):]
        syn = np.zeros(D, dtype=np.uint8)
        # slice 0: first ancilla round vs ideal (0 for both bases)
        for c in range(d - 1):
            syn[c] = anc[c]
        # slices 1..rounds-1: consecutive ancilla differences
        for t in range(1, rounds):
            for c in range(d - 1):
                syn[t * (d - 1) + c] = anc[t * (d - 1) + c] ^ anc[(t - 1) * (d - 1) + c]
        # final slice: data-readout parities vs last ancilla round
        for c in range(d - 1):
            syn[rounds * (d - 1) + c] = (dat[c] ^ dat[c + 1]) ^ anc[(rounds - 1) * (d - 1) + c]
        syndromes.append(syn)
        logicals.append(sum(dat) % 2)
        mult.append(n)
    return syndromes, logicals, mult
