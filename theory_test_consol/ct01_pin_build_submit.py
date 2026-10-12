#!/usr/bin/env python
"""ct01_pin_build_submit.py — consolidation campaign driver.

Discipline (identical to campaign 1, extended to two devices):
  1. Fresh full-properties snapshots of BOTH devices saved + digest-pinned.
  2. Layouts selected from those snapshots by the pinned rule; selection
     CSV digest-pinned.
  3. predictions_consol_<ts>.json written and SHA-256-pinned BEFORE any
     QPU submission (snapshots/selection are classical reads).
  4. Noiseless Aer end-to-end validation of every deterministic arm and a
     stochastic sample; submission ABORTS on any failed check.
  5. SamplerV2 submission: 4 jobs on ibm_marrakesh (det_z/det_x/stoch_z/
     stoch_x) + 2 jobs on ibm_fez (det_z/det_x).

Usage:
  python ct01_pin_build_submit.py --dry-run   # everything except QPU
  python ct01_pin_build_submit.py             # pin + validate + submit
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ct_common import (BACKEND_A, BACKEND_B, CIRC, D_OF, DET_INJ, OPT_LEVEL,
                       PATH, PRED, RES, ROUNDS, SHOTS_DET, SHOTS_STOCH, SNAP,
                       STOCH_PS, T_OF, TOKEN_PATH, arm_list, binom_tail,
                       build_rep_circuit_inj, canonical_circuit_digest,
                       dump_json, lambda_N, longest_path, poisson_tail,
                       select_lines, sha256_file, snapshot_props,
                       stable_seed, stoch_mask, verify_path, wilson95)

DRY = "--dry-run" in sys.argv
TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def get_service():
    from qiskit_ibm_runtime import QiskitRuntimeService
    token = json.loads(TOKEN_PATH.read_text())["token"]
    return QiskitRuntimeService(channel="ibm_quantum_platform", token=token)


def snapshot_full(service, name):
    backend = service.backend(name)
    out = {"backend_name": name, "backend_version": backend.version,
           "snapshot_utc": datetime.now(timezone.utc).strftime(
               "%Y%m%dT%H%M%SZ"),
           "num_qubits": backend.num_qubits,
           "purpose": "consolidation campaign line selection + lambda_N"}
    props = backend.properties()
    out["properties"] = props.to_dict()
    out["calibration_last_update"] = str(props.last_update_date)
    p = SNAP / f"{name}_snapshot_{TS}_consol.json"
    dump_json(p, out)
    return backend, p


def build_predictions(snap_info, layouts, sel_digests, paths_used, lams):
    """The pinned pre-registration document."""
    pis = {}
    for dev, per_code in lams.items():
        pis[dev] = {}
        for code, lam in per_code.items():
            t = T_OF[code]
            pis[dev][code] = {"lambda_N": lam,
                              **{f"pi{k}": poisson_tail(lam, k)
                                 for k in (1, 2, 3, 4)}}
    proto = {
        "TOL_DET": 0.005, "TOL_STOCH": 0.002,
        "SHARP_MIN": {"REP3": 0.85, "REP5": 0.90, "REP7": 0.90},
        "rounds": ROUNDS, "injection_round": 2,
        "seed_formula": "stable_seed('INJTT', code, basis, arm/p, variant)"
                        " (identical to campaign 1 -> identical masks)",
        "transpile_seed_formula": "stable_seed('INJTT', code, basis, name, 0)"
                                  " per device",
        "optimization_level": OPT_LEVEL,
        "estimator": ("lambda_N = sum_{data} ro + rounds*sum_{anc} ro "
                      "(symmetric readout, pinned snapshot); "
                      "pi(k) = Pr[Pois(lambda_N) >= k]"),
        "composed_stoch_rule": ("LFR(p) <= d0_hi + Pr[Bin(d,p)+Pois(lambda_N)"
                                " >= t+1] + TOL_STOCH"),
        "naive_stoch_rule": "LFR(p) <= d0_hi + BinomTail(d,t,p) + TOL_STOCH",
        "tests": []}
    # decision-rule tests per device
    for dev, codes in (("A", ("REP3", "REP5", "REP7")), ("B", ("REP5",))):
        for code in codes:
            t = T_OF[code]
            wc = [k for k in DET_INJ[code] if len(DET_INJ[code][k]) <= t]
            sh = [k for k in DET_INJ[code] if len(DET_INJ[code][k]) == t + 1]
            for basis in ("Z", "X"):
                for k in wc:
                    proto["tests"].append({
                        "device": dev, "code": code, "basis": basis,
                        "arm": k, "type": "bound",
                        "rule": "LFR_arm <= LFR_base + 0.005"})
                for k in sh:
                    proto["tests"].append({
                        "device": dev, "code": code, "basis": basis,
                        "arm": k, "type": "sharp",
                        "rule": f"LFR_arm >= {proto['SHARP_MIN'][code]}"})
                if dev == "A" and code == "REP5":
                    for p in STOCH_PS:
                        proto["tests"].append({
                            "device": dev, "code": code, "basis": basis,
                            "arm": f"p{p}", "type": "stochastic",
                            "binom_tail": binom_tail(5, t, p),
                            "rule": "naive + composed (formulas pinned)"})
    preds = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "campaign": "consolidation-2026-09-06",
        "purpose": ("pre-registered replication of the 2026-08-28 "
                    "injection-budget test on a new calibration cycle, "
                    "REP7 distance extension, and second-device check"),
        "reference_campaign": {
            "date": "2026-08-28", "backend": "ibm_marrakesh",
            "predictions_sha256":
                "759169c2024d54423fd1a5eb54d46b6501fd5d9f2cd4e1e49b18978c74653cd5",
            "jobs": ["da8um21qtnsc73d0v3ug", "da8um2ce74ec73aj4n3g",
                     "da8um31qtnsc73d0v400", "da8um3ke74ec73aj4n50"]},
        "devices": {"A": BACKEND_A, "B": BACKEND_B},
        "snapshots": snap_info,
        "reference_path": PATH,
        "paths_used": paths_used,
        "layouts": layouts,
        "layout_selection": {
            "rule": ("rank-1 contiguous window of the verified SWAP-free "
                     "reference path under the snapshot-only metrology "
                     "score of active_provenance/ap01 (readout + idle + "
                     "CZ), per length 5/9/13; selection CSVs digest-pinned"),
            "selection_csv_sha256": sel_digests},
        "lambda_N": lams, "pi": pis,
        "expectations": [
            "A: all bound tests hold; all sharp tests sharp",
            "A: naive stochastic bound falsified at p=0.10 both sectors"
            " (replication of the campaign-1 falsification)",
            "A: composed stochastic bound holds on all six cells",
            "A: REP7 w3 (=t) within bound; w4 (=t+1) >= 0.90 (third "
            "distance point on the weight cliff)",
            "B: REP5 qualitative pattern reproduces on ibm_fez",
            "A-vs-2026-08-28: every overlapping deterministic arm "
            "reproduces its campaign-1 verdict (bound/sharp)"],
        "protocol": proto}
    return preds


def aer_validate(layouts_unused=None):
    """Noiseless end-to-end check of all det arms + stochastic sample.
    Mirrors tt00_simulate.py. Returns True iff all checks pass."""
    from qiskit_aer import AerSimulator
    from qiskit import transpile
    from pymatching import Matching
    from ct_common import build_dem, counts_to_observables
    sim = AerSimulator()
    arms = arm_list(("A", "B"))
    det = [a for a in arms if a["kind"] == "det"]
    stoch = [a for a in arms if a["kind"] == "stoch"
             and a["variant"] < 3]
    print(f"[sim] {len(det)} det + {len(stoch)} stoch-sample arms "
          f"(noiseless, 512 shots)")
    bad = 0
    for a in det + stoch:
        d = D_OF[a["code"]]
        qc = build_rep_circuit_inj(d, a["basis"], ROUNDS, inject=a["inject"])
        tqc = transpile(qc, sim)
        counts = dict(sim.run(tqc, shots=512).result().get_counts())
        H, w, faults = build_dem(d, ROUNDS)
        m = Matching.from_check_matrix(H, weights=w, faults_matrix=faults)
        syndromes, logicals, mult = counts_to_observables(counts, d, ROUNDS)
        shots = fails = 0
        for syn, log, n in zip(syndromes, logicals, mult):
            pred = int(m.decode(syn)[0])
            shots += n
            fails += n * ((log ^ pred) != 0)
        ler = fails / shots
        tag = f"{a['campaign']}:{a['code']}-{a['basis']}-{a['name']}"
        if a["kind"] == "det":
            t = T_OF[a["code"]]
            wgt = 0 if a["name"] == "base" else int(a["name"][1])
            expect = "FAIL" if wgt == t + 1 else "ok"
            got = "FAIL" if ler > 0.5 else ("ok" if ler == 0 else "MIXED")
            status = "PASS" if expect == got else "CHECK"
        else:
            status = "PASS" if ler == 0 else "CHECK"
        if status != "PASS":
            bad += 1
            print(f"  {tag:34s} LFR={ler:.4f}  [{status}]")
    print(f"[sim] {'ALL PASS' if bad == 0 else f'{bad} ARMS FAILED'}"
          f" ({len(det)+len(stoch)} arms)")
    return bad == 0


def main():
    service = get_service()

    # ---- 1. fresh snapshots (classical) ----
    backend_a, snap_a = snapshot_full(service, BACKEND_A)
    backend_b, snap_b = snapshot_full(service, BACKEND_B)
    snap_info, qprops, czmap = {}, {}, {}
    for dev, p in (("A", snap_a), ("B", snap_b)):
        payload = json.loads(p.read_text())
        snap_info[dev] = {"file": p.name, "sha256": sha256_file(p),
                          "snapshot_utc": payload["snapshot_utc"],
                          "backend_version": payload["backend_version"],
                          "calibration_last_update":
                              payload["calibration_last_update"]}
        qprops[dev], czmap[dev] = snapshot_props(payload["properties"])
        print(f"[snapshot] {dev}={payload['backend_name']} "
              f"{p.name} sha256={snap_info[dev]['sha256'][:16]}...")

    # ---- 2. layout selection ----
    import csv
    layouts, sel_digests, paths_used = {}, {}, {}
    for dev in ("A", "B"):
        path = PATH if verify_path(PATH, czmap[dev]) else longest_path(
            czmap[dev], 156)
        paths_used[dev] = path
        lengths = (5, 9, 13) if dev == "A" else (9,)
        sel, rows = select_lines(qprops[dev], czmap[dev], lengths, path)
        layouts[dev] = {}
        for n, line in sel.items():
            code = {5: "REP3", 9: "REP5", 13: "REP7"}[n]
            layouts[dev][code] = line
        sel_path = RES / f"ct_line_selection_{dev}_{TS}.csv"
        with open(sel_path, "w", newline="") as f:
            wcsv = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            wcsv.writeheader()
            wcsv.writerows(rows)
        sel_digests[dev] = sha256_file(sel_path)
        print(f"[layout] {dev}: " +
              ", ".join(f"{c}={l}" for c, l in layouts[dev].items()) +
              f" (selection sha256={sel_digests[dev][:16]}...)")

    # ---- 3. lambda_N / pi from the pinned snapshots ----
    lams = {}
    for dev in ("A", "B"):
        ro = {q: qp["ro"] for q, qp in qprops[dev].items()}
        lams[dev] = {code: lambda_N(line, ro)
                     for code, line in layouts[dev].items()}
        print(f"[lambda_N] {dev}: " +
              ", ".join(f"{c}={v:.3f}" for c, v in lams[dev].items()))

    # ---- 4. pin predictions BEFORE any QPU ----
    preds = build_predictions(snap_info, layouts, sel_digests,
                              paths_used, lams)
    pred_path = PRED / f"predictions_consol_{TS}.json"
    dump_json(pred_path, preds)
    pred_digest = sha256_file(pred_path)
    print(f"[pin] predictions: {pred_path.name} sha256={pred_digest}")

    # ---- 5. noiseless validation (aborts submission on failure) ----
    if not aer_validate():
        print("[abort] noiseless validation failed; NOT submitting.")
        sys.exit(2)

    # ---- 6. build + transpile ----
    from qiskit import qpy, transpile
    backends = {"A": backend_a, "B": backend_b}
    arms = arm_list(("A", "B"))
    meta = {"script": "ct01_pin_build_submit.py",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "predictions_file": pred_path.name,
            "predictions_sha256": pred_digest,
            "optimization_level": OPT_LEVEL,
            "devices": {"A": BACKEND_A, "B": BACKEND_B},
            "layouts": layouts, "circuits": []}
    pubs = []
    for a in arms:
        d = D_OF[a["code"]]
        qc = build_rep_circuit_inj(d, a["basis"], ROUNDS, inject=a["inject"])
        line = layouts[a["campaign"]][a["code"]]
        seed = stable_seed("INJTT", a["campaign"], a["code"], a["basis"],
                           a["name"])
        name = f"{a['campaign'].lower()}_{a['code'].lower()}_" \
               f"{a['basis'].lower()}_{a['name']}"
        tqc = transpile(qc, backend=backends[a["campaign"]],
                        optimization_level=OPT_LEVEL,
                        initial_layout=line, seed_transpiler=seed)
        qpy_path = CIRC / f"{name}.qpy"
        with open(qpy_path, "wb") as f:
            qpy.dump(tqc, f)
        entry = {k: a[k] for k in ("campaign", "code", "basis", "name",
                                   "kind", "shots")}
        if a["kind"] == "stoch":
            entry.update(p=a["p"], variant=a["variant"], mask=a["mask"])
        entry.update(initial_layout=line, seed_transpiler=seed,
                     file=f"circuits/{name}.qpy",
                     sha256=canonical_circuit_digest(tqc),
                     qpy_sha256=sha256_file(qpy_path), depth=tqc.depth())
        meta["circuits"].append(entry)
        pubs.append((a, tqc))
    dump_json(CIRC / "circuits_metadata_consol.json", meta)
    print(f"[build] {len(pubs)} circuits transpiled + digested")
    if DRY:
        print("[dry-run] no submission.")
        return

    # ---- 7. submit ----
    from qiskit_ibm_runtime import SamplerV2
    jobs = []
    groups = {}
    for a, tqc in pubs:
        groups.setdefault((a["campaign"], a["kind"], a["basis"]),
                          []).append((a, tqc))
    for (camp, kind, basis), items in sorted(groups.items()):
        sampler = SamplerV2(mode=backends[camp])
        shots = SHOTS_DET if kind == "det" else SHOTS_STOCH
        job = sampler.run([t for _, t in items], shots=shots)
        jid = job.job_id()
        for a, _ in items:
            jobs.append({"job_id": jid,
                         "group": f"{camp}_{kind}_{basis.lower()}",
                         "campaign": camp, "code": a["code"],
                         "basis": basis, "name": a["name"], "shots": shots})
        print(f"[submit] {camp}_{kind}_{basis.lower()}: job {jid}, "
              f"{len(items)} pubs x {shots} shots")
    dump_json(RES / "consol_jobs.json", {
        "submitted_utc": datetime.now(timezone.utc).isoformat(),
        "predictions_file": pred_path.name,
        "predictions_sha256": pred_digest, "jobs": jobs})
    print("[done] job IDs saved to results/consol_jobs.json")


if __name__ == "__main__":
    main()
