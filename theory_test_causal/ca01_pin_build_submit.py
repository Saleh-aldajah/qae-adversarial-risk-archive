#!/usr/bin/env python
"""ca01_pin_build_submit.py -- causal hardware-ablation campaign driver
(campaign 3).

Converts the manuscript's simulation-only hardware ablations into causal
claims on ibm_marrakesh using experimenter-controlled knobs:

  Arm D  decoherence dose-response: REP5-Z memory with per-round idle
         delays of 0/1000/2000/4000 ns on every qubit (4 pubs x 10k).
  Arm P  placement ablation: REP5-Z base on 8 windows of the verified
         reference path, ranks 0-3 (best) and last-4 (worst) by the
         pinned snapshot metrology score (8 pubs x 10k).
  Arm T  interval tightening: 4x-shot re-run (50 variants x 800) of the
         consolidation stochastic cell with the widest archived Wilson
         interval (rule-selected from the archived CSV at pin time).

Discipline identical to campaigns 1-2:
  snapshot -> pinned-rule selection -> predictions JSON + SHA-256 pins
  BEFORE any QPU submission -> noiseless Aer validation (aborts on
  failure) -> SamplerV2 submission (3 jobs: D, P, T).

Usage:
  python ca01_pin_build_submit.py --selftest   # noiseless only, no quota
  python ca01_pin_build_submit.py --dry-run    # everything except QPU
  python ca01_pin_build_submit.py              # pin + validate + submit
"""
import csv
import json
import sys
from datetime import datetime, timezone

import numpy as np

from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from ca_common import (ARCHIVE_CONSOL_CSV, BACKEND, CAMPAIGN, CIRC,
                       DOSE_BASIS, DOSE_D, DOSES_NS, N_PLACE_BEST,
                       N_PLACE_WORST, PLACE_SHOTS, PRED, RES, SNAP,
                       TIGHTEN_SHOTS, build_rep_circuit_dose,
                       pick_tightening_cell)
from ct_common import (OPT_LEVEL, PATH, TOKEN_PATH, canonical_circuit_digest,
                       dump_json, line_score, longest_path, select_lines,
                       sha256_file, snapshot_props, stable_seed, verify_path,
                       wilson95)
from tt_common import (D_OF, INJ_ROUND, ROUNDS, SHOTS_DET, build_dem,
                       build_rep_circuit_inj, counts_to_observables,
                       stoch_mask)
from ct01_pin_build_submit import get_service, snapshot_full

DRY = "--dry-run" in sys.argv
SELFTEST = "--selftest" in sys.argv
TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def dose_arms():
    return [dict(arm="D", code="REP5", basis=DOSE_BASIS,
                 name=f"dose{D:g}ns", dose_ns=D, shots=SHOTS_DET)
            for D in DOSES_NS]


def place_arms(windows):
    return [dict(arm="P", code="REP5", basis=DOSE_BASIS,
                 name=f"place_r{rank}", rank=rank, window=w,
                 shots=PLACE_SHOTS)
            for rank, w in windows]


def tighten_arms(cell):
    p, basis = cell["p"], cell["basis"]
    out = []
    for v in range(50):
        mask = stoch_mask(cell["code"], basis, p, v)
        inj = {INJ_ROUND: [("X", j) for j in mask]} if mask else None
        out.append(dict(arm="T", code=cell["code"], basis=basis,
                        name=f"p{p}_v{v:02d}", p=p, variant=v, mask=mask,
                        inject=inj, shots=TIGHTEN_SHOTS))
    return out


def select_place_windows(qprops, cz, path):
    """Pinned rule: all contiguous 9-qubit windows of the verified
    reference path scored by the snapshot-only metrology score; take
    ranks 0..N_BEST-1 and the last N_WORST.  Deterministic."""
    assert verify_path(path, cz), "reference path broken in this snapshot"
    n = 9
    cands = [path[i:i + n] for i in range(len(path) - n + 1)]
    scored = sorted(((line_score(w, qprops, cz), w) for w in cands),
                    key=lambda t: (t[0], t[1]))
    rows = [{"length": n, "line": "-".join(map(str, w)), "score": f"{sc:.6f}",
             "rank": r} for r, (sc, w) in enumerate(scored)]
    picks = [(r, w) for r, (sc, w) in enumerate(scored[:N_PLACE_BEST])]
    picks += [(len(scored) - 1 - i, w)
              for i, (sc, w) in enumerate(reversed(scored[-N_PLACE_WORST:]))]
    picks.sort(key=lambda t: t[0])
    return picks, rows


def build_predictions(snap_info, cell, sel_digest, best_line, place_picks):
    proto = {
        "rounds": ROUNDS, "d": DOSE_D, "basis_D_P": DOSE_BASIS,
        "doses_ns": list(DOSES_NS),
        "dose_rule": ("uniform per-round idle delay on all qubits, rounds-1 "
                      "insertions; total added idle = (rounds-1)*dose"),
        "tests": [
            {"id": "D1", "type": "primary",
             "rule": ("one-sided two-proportion z: LFR(4000ns) > LFR(0ns) "
                      "at alpha=0.01; causal claim on gate/idle decoherence")},
            {"id": "D2", "type": "descriptive",
             "rule": "LFR monotone non-decreasing across the dose ladder"},
            {"id": "P1", "type": "primary",
             "rule": ("Spearman rho(window metrology rank, measured LFR "
                      "rank) >= 0.75 across the 8 placements")},
            {"id": "P2", "type": "primary",
             "rule": ("one-sided two-proportion z: pooled worst-4 LFR > "
                      "pooled best-4 LFR at alpha=0.01")},
            {"id": "T1", "type": "tightening",
             "rule": ("merged Wilson 95% width strictly below the archived "
                      "width; no pass/fail bound verdict re-rendered")}],
        "tightening_cell": cell,
        "tightening_rule": ("aggregate archived consolidation stoch rows by "
                            "(code,basis,p); widest pooled Wilson 95% cell "
                            "with >=1 failure; re-run all 50 variants at 4x"),
        "place_rule": ("contiguous 9-qubit windows of the verified reference "
                       "path ranked by the pinned snapshot-only metrology "
                       "score (readout + idle + CZ); ranks 0-3 and last-4"),
        "transpile_seed_formula": "stable_seed('INJCA', arm, code, basis, name)",
        "optimization_level": OPT_LEVEL,
        "shots": {"D": SHOTS_DET, "P": PLACE_SHOTS, "T": TIGHTEN_SHOTS},
        "noiseless_gate": ("every D and P pub must decode to LFR=0 under "
                           "noiseless Aer; T sample variants with mask "
                           "weight <= 2 must decode to 0 fails")}
    return {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "campaign": "causal-ablation-2026",
        "purpose": ("convert simulation-only hardware ablations (SWAP "
                    "routing/placement, gate/idle decoherence) into causal "
                    "device claims, and tighten the widest archived "
                    "stochastic interval"),
        "reference_campaigns": {
            "campaign1": {"date": "2026-08-28", "backend": "ibm_marrakesh"},
            "consolidation": {"date": "2026-09-06",
                              "backends": ["ibm_marrakesh", "ibm_fez"]}},
        "device": BACKEND,
        "snapshots": snap_info,
        "best_line": best_line,
        "place_picks": [{"rank": r, "window": w} for r, w in place_picks],
        "place_selection_csv_sha256": sel_digest,
        "protocol": proto}


def aer_validate(tcell):
    """Noiseless end-to-end check per the pinned gate.  dt for circuit
    construction is nominal (0.222 ns); delays have no effect noiselessly."""
    from qiskit import transpile
    from qiskit_aer import AerSimulator
    from pymatching import Matching
    sim = AerSimulator()
    bad = 0
    checks = []
    for D in DOSES_NS:
        qc = build_rep_circuit_dose(DOSE_D, DOSE_BASIS, ROUNDS, D, 0.222)
        checks.append((f"D-dose{D:g}ns", qc, "zero"))
    qc = build_rep_circuit_inj(DOSE_D, DOSE_BASIS, ROUNDS, inject=None)
    checks.append(("P-base", qc, "zero"))
    for a in tighten_arms(tcell)[:3]:
        qc = build_rep_circuit_inj(D_OF[a["code"]], a["basis"], ROUNDS,
                                   inject=a["inject"])
        w = len(a["mask"])
        checks.append((f"T-p{a['p']}_v{a['variant']:02d}", qc,
                       "zero" if w <= 2 else "free"))
    print(f"[sim] {len(checks)} noiseless checks (512 shots)")
    for tag, qc, expect in checks:
        tqc = transpile(qc, sim)
        counts = dict(sim.run(tqc, shots=512).result().get_counts())
        H, w_, faults = build_dem(DOSE_D, ROUNDS)
        m = Matching.from_check_matrix(H, weights=w_, faults_matrix=faults)
        syndromes, logicals, mult = counts_to_observables(counts, DOSE_D,
                                                          ROUNDS)
        shots = fails = 0
        for syn, log, n_ in zip(syndromes, logicals, mult):
            pred = int(m.decode(syn)[0])
            shots += n_
            fails += n_ * ((log ^ pred) != 0)
        ok = (expect == "free") or (fails == 0)
        if not ok:
            bad += 1
            print(f"  {tag:22s} fails={fails}/{shots} [FAIL]")
    print(f"[sim] {'ALL PASS' if bad == 0 else f'{bad} FAILED'}")
    return bad == 0


def main():
    tcell = pick_tightening_cell(ARCHIVE_CONSOL_CSV)
    print(f"[rule] tightening cell: {tcell['code']}-{tcell['basis']} "
          f"p={tcell['p']} archived {tcell['failures']}/{tcell['shots']} "
          f"width={tcell['ci_hi']-tcell['ci_lo']:.5f}")

    if SELFTEST:
        ok = aer_validate(tcell)
        print("SELFTEST PASS" if ok else "SELFTEST FAIL")
        sys.exit(0 if ok else 1)

    service = get_service()
    backend, snap = snapshot_full(service, BACKEND)
    payload = json.loads(snap.read_text())
    snap_info = {"file": snap.name, "sha256": sha256_file(snap),
                 "snapshot_utc": payload["snapshot_utc"],
                 "backend_version": payload["backend_version"],
                 "calibration_last_update":
                     payload["calibration_last_update"]}
    qprops, czmap = snapshot_props(payload["properties"])
    print(f"[snapshot] {payload['backend_name']} {snap.name} "
          f"sha256={snap_info['sha256'][:16]}...")

    path = PATH if verify_path(PATH, czmap) else longest_path(czmap, 156)
    sel, _rows = select_lines(qprops, czmap, (9,), path)
    best_line = sel[9]
    picks, rows = select_place_windows(qprops, czmap, path)
    sel_path = RES / f"ca_place_selection_{TS}.csv"
    with open(sel_path, "w", newline="") as f:
        wcsv = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wcsv.writeheader()
        wcsv.writerows(rows)
    sel_digest = sha256_file(sel_path)
    print(f"[layout] best={best_line}; placements "
          f"{[r for r, _ in picks]} (sel sha256={sel_digest[:16]}...)")

    preds = build_predictions(snap_info, tcell, sel_digest, best_line, picks)
    pred_path = PRED / f"predictions_causal_{TS}.json"
    dump_json(pred_path, preds)
    pred_digest = sha256_file(pred_path)
    print(f"[pin] predictions: {pred_path.name} sha256={pred_digest}")

    if not aer_validate(tcell):
        print("[abort] noiseless validation failed; NOT submitting.")
        sys.exit(2)

    from qiskit import qpy, transpile
    dt = backend.dt or 0.222e-9
    dt_ns = dt * 1e9
    arms = dose_arms() + place_arms(picks) + tighten_arms(tcell)
    meta = {"script": "ca01_pin_build_submit.py",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "predictions_file": pred_path.name,
            "predictions_sha256": pred_digest,
            "device": BACKEND, "dt_ns": dt_ns, "circuits": []}
    pubs = []
    for a in arms:
        if a["arm"] == "D":
            qc = build_rep_circuit_dose(DOSE_D, a["basis"], ROUNDS,
                                        a["dose_ns"], dt_ns)
            line = best_line
        elif a["arm"] == "P":
            qc = build_rep_circuit_inj(DOSE_D, a["basis"], ROUNDS,
                                       inject=None)
            line = a["window"]
        else:
            qc = build_rep_circuit_inj(D_OF[a["code"]], a["basis"], ROUNDS,
                                       inject=a["inject"])
            line = best_line
        seed = stable_seed("INJCA", a["arm"], a["code"], a["basis"],
                           a["name"])
        name = f"c_{a['arm'].lower()}_{a['code'].lower()}_{a['basis'].lower()}_{a['name']}"
        tqc = transpile(qc, backend=backend, optimization_level=OPT_LEVEL,
                        initial_layout=line, seed_transpiler=seed)
        qpy_path = CIRC / f"{name}.qpy"
        with open(qpy_path, "wb") as f:
            qpy.dump(tqc, f)
        entry = {k: v for k, v in a.items() if k != "inject"}
        entry.update(initial_layout=line, seed_transpiler=seed,
                     file=f"circuits/{name}.qpy",
                     sha256=canonical_circuit_digest(tqc),
                     qpy_sha256=sha256_file(qpy_path), depth=tqc.depth())
        meta["circuits"].append(entry)
        pubs.append((a, tqc))
    dump_json(CIRC / "circuits_metadata_causal.json", meta)
    print(f"[build] {len(pubs)} circuits transpiled + digested")
    if DRY:
        print("[dry-run] no submission.")
        return

    from qiskit_ibm_runtime import SamplerV2
    jobs = []
    for arm_tag in ("D", "P", "T"):
        items = [(a, t) for a, t in pubs if a["arm"] == arm_tag]
        sampler = SamplerV2(mode=backend)
        shots = items[0][0]["shots"]
        job = sampler.run([t for _, t in items], shots=shots)
        jid = job.job_id()
        for a, _ in items:
            jobs.append({"job_id": jid, "group": f"C_{arm_tag}",
                         "campaign": CAMPAIGN, "arm": arm_tag,
                         "code": a["code"], "basis": a["basis"],
                         "name": a["name"], "shots": shots})
        print(f"[submit] C_{arm_tag}: job {jid}, {len(items)} pubs x "
              f"{shots} shots")
    dump_json(RES / "causal_jobs.json", {
        "submitted_utc": datetime.now(timezone.utc).isoformat(),
        "predictions_file": pred_path.name,
        "predictions_sha256": pred_digest, "jobs": jobs})
    print("[done] job IDs saved to results/causal_jobs.json")


if __name__ == "__main__":
    main()
