#!/usr/bin/env python
"""tt00_simulate.py — noiseless end-to-end validation BEFORE QPU submission.

Runs every deterministic arm and a sample of stochastic variants through
qiskit's StatevectorSampler (no noise), then through the SAME parsing +
MWPM decode pipeline used for hardware counts. Expected (ideal theory):
  REP5: base 0, w2 0, w3 ~1 | REP3: base 0, w1 0, w2 ~1 | stochastic ~0.
Any deviation flags a circuit/parsing bug, not physics.
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tt_common import (D_OF, ROUNDS, arm_list, build_dem,  # noqa: E402
                       build_rep_circuit_inj, counts_to_observables)

SHOTS = 512


def simulate_counts(qc, shots=SHOTS):
    from qiskit_aer import AerSimulator
    from qiskit import transpile
    sim = AerSimulator()
    tqc = transpile(qc, sim)
    res = sim.run(tqc, shots=shots).result()
    return dict(res.get_counts())


def decode_counts(counts, d):
    from pymatching import Matching
    H, w, faults = build_dem(d, ROUNDS)
    m = Matching.from_check_matrix(H, weights=w, faults_matrix=faults)
    syndromes, logicals, mult = counts_to_observables(counts, d, ROUNDS)
    shots = failures = 0
    for syn, log, n in zip(syndromes, logicals, mult):
        pred = int(m.decode(syn)[0])
        shots += n
        failures += n * ((log ^ pred) != 0)
    return shots, failures


def main():
    arms = arm_list()
    det = [a for a in arms if a["kind"] == "det"]
    stoch = [a for a in arms if a["kind"] == "stoch" and a["variant"] < 5
             and abs(a["p"] - 0.10) < 1e-9]
    print(f"[sim] {len(det)} deterministic + {len(stoch)} sampled stochastic arms "
          f"(noiseless, {SHOTS} shots)")
    bad = 0
    for a in det + stoch:
        d = D_OF[a["code"]]
        qc = build_rep_circuit_inj(d, a["basis"], ROUNDS, inject=a["inject"])
        counts = simulate_counts(qc)
        shots, fails = decode_counts(counts, d)
        ler = fails / shots
        tag = f"{a['code']}-{a['basis']}-{a['name']}"
        if a["kind"] == "det":
            t = {"REP3": 1, "REP5": 2}[a["code"]]
            w = 0 if a["name"] == "base" else int(a["name"][1])
            expect = "FAIL" if w == t + 1 else "ok"
            got = "FAIL" if ler > 0.5 else ("ok" if ler == 0 else "MIXED")
            status = "PASS" if expect == got else "CHECK"
        else:
            status = "PASS" if ler == 0 else "CHECK"
        if status != "PASS":
            bad += 1
        print(f"  {tag:28s} LFR={ler:.4f}  [{status}]")
    print(f"[sim] {'ALL PASS' if bad == 0 else f'{bad} arms need review'}")


if __name__ == "__main__":
    main()
