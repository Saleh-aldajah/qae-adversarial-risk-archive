#!/usr/bin/env python
"""ct_common.py — shared machinery for the CONSOLIDATION campaign
(pre-registered replication + REP7 extension + second device).

Campaign A (ibm_marrakesh, 2026-09-06 calibration cycle):
  * deterministic REP3/REP5 arms — exact replication of the 2026-08-28
    pre-registered test (same injections, same decision rules, same
    stochastic masks via the same seed formula)
  * deterministic REP7 arms (d=7, t=3): NEW third distance point on the
    weight cliff — arms base / w3 (=t, worst-case central string) /
    w4 (=t+1, central string), both sectors
  * stochastic REP5 cells p in {0.01, 0.05, 0.10}, 50 pinned variants x
    200 shots per sector (identical masks to campaign 1)
Campaign B (ibm_fez, second device):
  * deterministic REP5 arms only (base / w2 / w3, both sectors)

Native-fault estimator (EXPLICIT — pinned; resolves the underspecified
calibration estimate of campaign 1):
    lam_N(line) = sum_{q in data} ro(q) + ROUNDS * sum_{q in anc} ro(q)
with ro the symmetric readout error of the pinned fresh snapshot
(readout locations dominate the spacetime fault budget on Heron r2;
gate/idle terms are second order and conservatively neglected).
    pi(k) = Pr[Pois(lam_N) >= k]

Bit convention, circuits, DEM decode identical to theory_test (tt_common).
Token: readable handoff copy only; never printed.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "theory_test"))
sys.path.insert(0, str(HERE.parent / "ibm_demo"))

import ibm_demo_common as _idc
_idc.TOKEN_PATH = Path("/mnt/agents/temp/ibm_token.json")
import tt_common as _ttc
_ttc.TOKEN_PATH = _idc.TOKEN_PATH

from tt_common import (ROUNDS, INJ_ROUND, SHOTS_DET, SHOTS_STOCH,  # noqa: E402
                       STOCH_VARIANTS, STOCH_PS, OPT_LEVEL,
                       build_rep_circuit_inj, build_dem,
                       counts_to_observables, canonical_circuit_digest,
                       dump_json, sha256_file, stable_seed, wilson95,
                       binom_tail, stoch_mask)

TOKEN_PATH = _idc.TOKEN_PATH
BACKEND_A = "ibm_marrakesh"   # replication device (campaign 1: 2026-08-28)
BACKEND_B = "ibm_fez"         # second device

D_OF = {"REP3": 3, "REP5": 5, "REP7": 7}
T_OF = {"REP3": 1, "REP5": 2, "REP7": 3}

# Deterministic worst-case central-string injections at INJ_ROUND.
# REP3/REP5 identical to campaign 1 (tt_common.DET_INJ); REP7 new.
DET_INJ = {"REP3": {"w1": [("X", 1)], "w2": [("X", 0), ("X", 2)]},
           "REP5": {"w2": [("X", 2), ("X", 3)],
                    "w3": [("X", 1), ("X", 2), ("X", 3)]},
           "REP7": {"w3": [("X", 2), ("X", 3), ("X", 4)],
                    "w4": [("X", 1), ("X", 2), ("X", 3), ("X", 4)]}}

# SWAP-free reference path on the 156-qubit Heron heavy-hex (verified
# against each device snapshot before use).
PATH = list(range(16)) + [19, 35, 34, 33, 32]
W_IDLE_NS = 5404.0

CIRC = HERE / "circuits"
COUNTS = HERE / "counts"
RES = HERE / "results"
PRED = HERE / "predictions"
SNAP = HERE / "backend_snapshots"
for _p in (CIRC, COUNTS, RES, PRED, SNAP):
    _p.mkdir(exist_ok=True)

SEED_TAG = "INJTT"   # identical to campaign 1 -> identical stochastic masks


def poisson_tail(lam: float, k: int) -> float:
    """Pr[Pois(lam) >= k]."""
    from math import exp, factorial
    return 1.0 - sum(exp(-lam) * lam ** j / factorial(j) for j in range(k))


def lambda_N(line, ro, rounds=ROUNDS):
    """Readout-dominated native-fault rate (faults/shot) on a line.

    line: physical qubits [data0, anc0, data1, ..., anc_{d-2}, data_{d-1}]
    ro: dict qubit -> symmetric readout error from the pinned snapshot.
    """
    data = line[0::2]
    anc = line[1::2]
    return float(sum(ro[q] for q in data) + rounds * sum(ro[q] for q in anc))


def snapshot_props(props_json):
    """Extract {qubit: {T1,T2,ro,init}} and undirected cz error map from a
    qiskit BackendProperties.to_json() dict."""
    qub, gates = props_json["qubits"], props_json["gates"]

    def qp(q, name):
        for dd in qub[q]:
            if dd["name"] == name:
                return dd["value"]

    qprops = {}
    for q in range(len(qub)):
        ro = (qp(q, "prob_meas1_prep0") + qp(q, "prob_meas0_prep1")) / 2.0
        qprops[q] = {"T1": qp(q, "T1"), "T2": qp(q, "T2"),
                     "ro": ro, "init": qp(q, "init_error")}
    cz = {}
    for g in gates:
        if g["gate"] == "cz":
            a, b = g["qubits"]
            for pp in g["parameters"]:
                if pp["name"] == "gate_error":
                    cz[frozenset((a, b))] = pp["value"]
    return qprops, cz


def line_score(window, qprops, cz):
    """Snapshot-only metrology score (ap01 rule, score_snapshot_only)."""
    s = 0.0
    for q in window:
        qp = qprops[q]
        idle = W_IDLE_NS / 1000.0 * (1.0 / qp["T1"] + 1.0 / qp["T2"])
        s += qp["ro"] + idle
    for a, b in zip(window[:-1], window[1:]):
        s += cz[frozenset((a, b))]
    return s


def verify_path(path, cz):
    """All consecutive pairs must carry a cz edge in this snapshot."""
    return all(frozenset((a, b)) in cz for a, b in zip(path[:-1], path[1:]))


def longest_path(cz, nq):
    """Deterministic fallback: longest simple path, lowest-index start and
    lowest-index neighbour tie-breaks (heavy-hex has max degree 3)."""
    adj = {q: [] for q in range(nq)}
    for e in cz:
        a, b = sorted(e)
        adj[a].append(b)
        adj[b].append(a)
    for q in adj:
        adj[q].sort()
    best = []

    def dfs(u, seen, acc):
        nonlocal best
        if len(acc) > len(best):
            best = list(acc)
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                acc.append(v)
                dfs(v, seen, acc)
                acc.pop()
                seen.discard(v)

    for s in range(nq):
        dfs(s, {s}, [s])
    return best


def select_lines(qprops, cz, lengths=(5, 9, 13), path=None):
    """Rank all contiguous windows of the reference path per length;
    returns {length: (rank1_window, selection_rows)}. Deterministic."""
    path = path or PATH
    assert verify_path(path, cz), "reference path broken in this snapshot"
    out, rows = {}, []
    for n in lengths:
        cands = [path[i:i + n] for i in range(len(path) - n + 1)]
        scored = sorted(((line_score(w, qprops, cz), w) for w in cands),
                        key=lambda t: (t[0], t[1]))
        for rank, (sc, w) in enumerate(scored):
            rows.append({"length": n, "line": "-".join(map(str, w)),
                         "score": f"{sc:.6f}", "rank": rank})
        out[n] = scored[0][1]
    return out, rows


def arm_list(campaigns=("A", "B")):
    """Consolidation arm table.

    Arm dict: code, basis, name, kind (det/stoch), inject, shots, campaign.
    """
    arms = []
    if "A" in campaigns:
        for code in ("REP3", "REP5", "REP7"):
            for basis in ("Z", "X"):
                arms.append(dict(code=code, basis=basis, name="base",
                                 kind="det", inject=None, shots=SHOTS_DET,
                                 campaign="A"))
                for tag, faults in DET_INJ[code].items():
                    arms.append(dict(code=code, basis=basis, name=tag,
                                     kind="det",
                                     inject={INJ_ROUND: list(faults)},
                                     shots=SHOTS_DET, campaign="A"))
        for basis in ("Z", "X"):
            for p in STOCH_PS:
                for v in range(STOCH_VARIANTS):
                    mask = stoch_mask("REP5", basis, p, v)
                    inj = {INJ_ROUND: [("X", j) for j in mask]} if mask else None
                    arms.append(dict(code="REP5", basis=basis,
                                     name=f"p{p}_v{v:02d}", kind="stoch",
                                     p=p, variant=v, mask=mask, inject=inj,
                                     shots=SHOTS_STOCH, campaign="A"))
    if "B" in campaigns:
        for basis in ("Z", "X"):
            arms.append(dict(code="REP5", basis=basis, name="base",
                             kind="det", inject=None, shots=SHOTS_DET,
                             campaign="B"))
            for tag, faults in DET_INJ["REP5"].items():
                arms.append(dict(code="REP5", basis=basis, name=tag,
                                 kind="det",
                                 inject={INJ_ROUND: list(faults)},
                                 shots=SHOTS_DET, campaign="B"))
    return arms
