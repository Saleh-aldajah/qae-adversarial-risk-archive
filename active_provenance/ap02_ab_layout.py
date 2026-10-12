#!/usr/bin/env python
"""ap02_ab_layout.py — Active-provenance A/B hardware test (Stage-10).

Hypothesis: a metrology-informed, digest-bound layout selection (ap01)
lowers the logical error rate of a repetition-code memory vs the original
unoptimized line on the SAME device, SAME day (drift-controlled A/B).

Arms (8 jobs, 10,000 shots each, r=4, MWPM-DEM decode):
  A = original lines:  REP3 [0,1,2,3,4],          REP5 [0..8]
  B = selected lines:  REP3 [2,3,4,5,6],          REP5 [2..10]
  (B = rank-1 windows of ap_line_selection.csv; avoids q1 — measured
  readout-defect 3.43x snapshot — and q0, lowest-T2 qubit on the line.)

Provenance:
  * seed formula #16: seed_transpiler = stable_seed('IBMAB', code, basis,
    rounds, line_tag); optimization_level = 1 (pinned).
  * Selection binding: sha256 of results/ap_line_selection.csv recorded in
    every run record ("selection_digest").
  * Fresh same-day backend snapshot saved before submission.
  * Canonical op-sequence digest + QPY byte digest per circuit.

Modes:
  --submit    build, transpile, submit 8 jobs, save job IDs (fast).
  --retrieve  fetch counts for submitted jobs, save counts + run record.
  --decode    decode all retrieved counts (MWPM-DEM), A/B statistics.
"""
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DEMO = HERE.parent / "ibm_demo"
sys.path.insert(0, str(DEMO))

from ibm_demo_common import (BACKEND_NAME, OPT_LEVEL, TOKEN_PATH,  # noqa: E402
                             build_dem, build_rep_circuit,
                             canonical_circuit_digest, counts_to_observables,
                             dump_json, sha256_file, stable_seed, wilson95)

SHOTS = 10_000
ROUNDS = 4
LINES = {("REP3", "A"): [0, 1, 2, 3, 4], ("REP3", "B"): [2, 3, 4, 5, 6],
         ("REP5", "A"): [0, 1, 2, 3, 4, 5, 6, 7, 8],
         ("REP5", "B"): [2, 3, 4, 5, 6, 7, 8, 9, 10]}
D_OF = {"REP3": 3, "REP5": 5}

CIRC = HERE / "circuits"
COUNTS = HERE / "counts"
RES = HERE / "results"
for p in (CIRC, COUNTS, RES):
    p.mkdir(exist_ok=True)

SELECTION_DIGEST = sha256_file(RES / "ap_line_selection.csv")


def seed16(code, basis, rounds, line_tag):
    return stable_seed("IBMAB", code, basis, rounds, line_tag)


def get_service():
    from qiskit_ibm_runtime import QiskitRuntimeService
    token = json.loads(TOKEN_PATH.read_text())["token"]
    return QiskitRuntimeService(channel="ibm_quantum_platform", token=token)


def snapshot(service):
    backend = service.backend(BACKEND_NAME)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = {"backend_name": BACKEND_NAME, "backend_version": backend.version,
           "snapshot_utc": ts, "num_qubits": backend.num_qubits}
    try:
        props = backend.properties()
        out["properties"] = json.loads(props.to_json())
    except Exception as e:  # noqa: BLE001
        out["properties_error"] = str(e)
    try:
        out["target_summary"] = str(backend.target)
    except Exception:  # noqa: BLE001
        pass
    (HERE / "backend_snapshots").mkdir(exist_ok=True)
    p = HERE / "backend_snapshots" / f"ibm_marrakesh_snapshot_{ts}_ab.json"
    dump_json(p, out)
    return backend, p


def build_all(backend):
    from qiskit import qpy, transpile
    meta = {"script": "ap02_ab_layout.py",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "selection_digest": SELECTION_DIGEST,
            "seed_formula": "#16 stable_seed('IBMAB', code, basis, rounds, line)",
            "optimization_level": OPT_LEVEL, "shots": SHOTS, "rounds": ROUNDS,
            "circuits": []}
    pubs = []
    for (code, tag), line in LINES.items():
        d = D_OF[code]
        for basis in ("Z", "X"):
            qc = build_rep_circuit(d, basis, ROUNDS)
            seed = seed16(code, basis, ROUNDS, tag)
            tqc = transpile(qc, backend=backend, optimization_level=OPT_LEVEL,
                            initial_layout=line, seed_transpiler=seed)
            name = f"{code.lower()}_{basis.lower()}_r{ROUNDS}_{tag}"
            qpy_path = CIRC / f"{name}.qpy"
            with open(qpy_path, "wb") as f:
                qpy.dump(tqc, f)
            entry = {"code": code, "basis": basis, "rounds": ROUNDS,
                     "line": tag, "initial_layout": line,
                     "seed_transpiler": seed, "file": f"circuits/{name}.qpy",
                     "sha256": canonical_circuit_digest(tqc),
                     "qpy_sha256": sha256_file(qpy_path),
                     "depth": tqc.depth(), "ops": dict(tqc.count_ops())}
            meta["circuits"].append(entry)
            pubs.append((entry, tqc))
            print(f"built {name}: depth={tqc.depth()} layout={line}")
    dump_json(CIRC / "circuits_metadata_ab.json", meta)
    return pubs


def submit():
    service = get_service()
    backend, snap_path = snapshot(service)
    print("snapshot:", snap_path)
    pubs = build_all(backend)
    from qiskit_ibm_runtime import SamplerV2
    sampler = SamplerV2(mode=backend)
    jobs = []
    for entry, tqc in pubs:
        job = sampler.run([tqc], shots=SHOTS)
        jid = job.job_id()
        jobs.append({"job_id": jid, "code": entry["code"],
                     "basis": entry["basis"], "line": entry["line"],
                     "qpy_sha256": entry["qpy_sha256"]})
        print(f"submitted {entry['code']}-{entry['basis']}-{entry['line']}: {jid}",
              flush=True)
    dump_json(COUNTS / "ab_jobs.json",
              {"script": "ap02_ab_layout.py --submit",
               "timestamp_utc": datetime.now(timezone.utc).isoformat(),
               "backend": BACKEND_NAME, "shots": SHOTS,
               "selection_digest": SELECTION_DIGEST, "jobs": jobs})
    print("job IDs saved to counts/ab_jobs.json")


def retrieve():
    service = get_service()
    jobs = json.loads((COUNTS / "ab_jobs.json").read_text())["jobs"]
    record = {"script": "ap02_ab_layout.py --retrieve",
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "selection_digest": SELECTION_DIGEST, "runs": []}
    for j in jobs:
        job = service.job(j["job_id"])
        st = job.status()
        print(f"{j['job_id']} {j['code']}-{j['basis']}-{j['line']}: {st}",
              flush=True)
        if str(st) != "DONE" and str(st) != "JobStatus.DONE":
            continue
        res = job.result()[0]
        counts = res.data.meas.get_counts()
        name = f"counts_{j['code'].lower()}_{j['basis'].lower()}_r{ROUNDS}_{j['line']}_ab.json"
        payload = {"backend": BACKEND_NAME,
                   "backend_version": job.backend().version,
                   "execution_mode": "job", "job_id": j["job_id"],
                   "creation_time": str(getattr(job, "creation_date", None)),
                   "config": {"code": j["code"], "basis": j["basis"],
                              "rounds": ROUNDS, "line": j["line"],
                              "qpy_sha256": j["qpy_sha256"]},
                   "shots_requested": SHOTS,
                   "usage": (job.metrics().get("usage", {})
                             if hasattr(job, "metrics") else None),
                   "counts": counts}
        dump_json(COUNTS / name, payload)
        record["runs"].append({"code": j["code"], "basis": j["basis"],
                               "line": j["line"], "job_id": j["job_id"],
                               "counts_file": f"counts/{name}",
                               "counts_sha256": sha256_file(COUNTS / name)})
    dump_json(COUNTS / "run_record_ab.json", record)
    print(f"retrieved {len(record['runs'])}/8")


def decode():
    from pymatching import Matching

    def decode_counts(counts, d):
        H, w, faults = build_dem(d, ROUNDS)
        m = Matching.from_check_matrix(H, weights=w, faults_matrix=faults)
        syndromes, logicals, mult = counts_to_observables(counts, d, ROUNDS)
        shots = failures = 0
        for syn, log, n in zip(syndromes, logicals, mult):
            pred = int(m.decode(syn)[0])
            shots += n
            failures += n * ((log ^ pred) != 0)
        return shots, failures

    def det_rates(counts, d):
        nanc = d - 1
        shots = sum(counts.values())
        det = np.zeros((ROUNDS, nanc))
        for bs, k in counts.items():
            bits = bs[::-1]
            a = np.array([[int(bits[t * nanc + c]) for c in range(nanc)]
                          for t in range(ROUNDS)])
            dets = a.copy()
            dets[1:] = a[1:] ^ a[:-1]
            det += dets * k
        return det / shots

    rows = []
    detail = {}
    for code in ("REP3", "REP5"):
        d = D_OF[code]
        for basis in ("Z", "X"):
            arms = {}
            for tag in ("A", "B"):
                p = COUNTS / f"counts_{code.lower()}_{basis.lower()}_r{ROUNDS}_{tag}_ab.json"
                payload = json.loads(p.read_text())
                shots, fails = decode_counts(payload["counts"], d)
                lo, hi = wilson95(fails, shots)
                arms[tag] = dict(shots=shots, fails=fails, ler=fails / shots,
                                 lo=lo, hi=hi,
                                 det=det_rates(payload["counts"], d),
                                 job_id=payload["job_id"],
                                 usage=payload.get("usage"))
            a, b = arms["A"], arms["B"]
            p_pool = (a["fails"] + b["fails"]) / (a["shots"] + b["shots"])
            se = np.sqrt(p_pool * (1 - p_pool) * (1 / a["shots"] + 1 / b["shots"]))
            z = (b["ler"] - a["ler"]) / se if se > 0 else 0.0
            rows.append({"code": code, "basis": basis,
                         "A_fail": a["fails"], "A_shots": a["shots"],
                         "A_ler": f"{a['ler']:.6g}",
                         "A_ci": f"[{a['lo']:.3g}, {a['hi']:.3g}]",
                         "B_fail": b["fails"], "B_shots": b["shots"],
                         "B_ler": f"{b['ler']:.6g}",
                         "B_ci": f"[{b['lo']:.3g}, {b['hi']:.3g}]",
                         "z_B_minus_A": f"{z:+.3f}",
                         "A_job": a["job_id"], "B_job": b["job_id"]})
            detail[f"{code}-{basis}"] = {
                "A": {k: (v.tolist() if isinstance(v, np.ndarray) else v)
                      for k, v in a.items()},
                "B": {k: (v.tolist() if isinstance(v, np.ndarray) else v)
                      for k, v in b.items()},
                "z_B_minus_A": z}
            print(f"{code}-{basis}: A {a['fails']}/{a['shots']} "
                  f"({a['ler']:.3g})  B {b['fails']}/{b['shots']} "
                  f"({b['ler']:.3g})  z={z:+.2f}")

    # Cochran-Mantel-Haenszel pooled odds ratio across the 4 configs
    # (common OR of B vs A), plus a pooled z on the summed difference.
    num = den = 0.0
    var = 0.0
    for r in rows:
        nA, nB = float(r["A_shots"]), float(r["B_shots"])
        kA, kB = float(r["A_fail"]), float(r["B_fail"])
        n = nA + nB
        k = kA + kB
        num += kB - nB * k / n
        var += nA * nB * k * (n - k) / (n * n * (n - 1)) if n > 1 else 0.0
    z_cmh = num / np.sqrt(var) if var > 0 else 0.0
    print(f"CMH pooled z (B-A) across 4 strata: {z_cmh:+.2f}")

    with open(RES / "ap_ab_results.csv", "w", newline="") as f:
        wcsv = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wcsv.writeheader()
        wcsv.writerows(rows)
    dump_json(RES / "ap_ab_decode_detail.json",
              {"script": "ap02_ab_layout.py --decode",
               "timestamp_utc": datetime.now(timezone.utc).isoformat(),
               "selection_digest": SELECTION_DIGEST,
               "cmh_z": z_cmh, "configs": detail})
    print("wrote results/ap_ab_results.csv + ap_ab_decode_detail.json")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["submit", "retrieve", "decode"])
    args = ap.parse_args()
    {"submit": submit, "retrieve": retrieve, "decode": decode}[args.mode]()
