#!/usr/bin/env python
"""tt01_submit.py — pin predictions, build, transpile, submit the
injection-budget theory test to ibm_marrakesh.

Discipline (same as active-provenance):
  1. predictions_<ts>.json written and sha256-pinned BEFORE any QPU call.
  2. Fresh backend snapshot saved before submission.
  3. Canonical op-sequence digest + QPY byte digest per circuit.
  4. Token read programmatically from /mnt/agents/upload/ibm_token.json;
     never printed.

Usage: python tt01_submit.py            # pin + build + submit
       python tt01_submit.py --dry-run  # pin + build only (no QPU)
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "ibm_demo"))
import ibm_demo_common as _idc  # token handoff: readable copy only (never printed)
_idc.TOKEN_PATH = Path("/mnt/agents/temp/ibm_token.json")
import tt_common as _ttc
_ttc.TOKEN_PATH = _idc.TOKEN_PATH
from tt_common import (BACKEND_NAME, CIRC, OPT_LEVEL, PRED, RES,  # noqa: E402
                       SHOTS_DET, SHOTS_STOCH, TOKEN_PATH,
                       arm_list, build_rep_circuit_inj,
                       canonical_circuit_digest, dump_json, pin_predictions,
                       sha256_file, stable_seed)

DRY = "--dry-run" in sys.argv


def get_service():
    from qiskit_ibm_runtime import QiskitRuntimeService
    token = json.loads(TOKEN_PATH.read_text())["token"]
    return QiskitRuntimeService(channel="ibm_quantum_platform", token=token)


def snapshot(service):
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backend = service.backend(BACKEND_NAME)
    out = {"backend_name": BACKEND_NAME, "backend_version": backend.version,
           "snapshot_utc": ts, "num_qubits": backend.num_qubits,
           "purpose": "theory-test injection campaign"}
    try:
        props = backend.properties()
        out["t1"] = [props.t1(q) for q in range(12)]
        out["t2"] = [props.t2(q) for q in range(12)]
        out["readout_error"] = [props.readout_error(q) for q in range(12)]
    except Exception as e:  # noqa: BLE001
        out["props_error"] = str(e)
    out["target_summary"] = str(backend.target)
    snapdir = HERE / "backend_snapshots"
    snapdir.mkdir(exist_ok=True)
    p = snapdir / f"ibm_marrakesh_snapshot_{ts}_theorytest.json"
    dump_json(p, out)
    return backend, p


def main():
    # ---- 1. pin predictions BEFORE any QPU interaction ----
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    preds = pin_predictions()
    preds["created_utc"] = datetime.now(timezone.utc).isoformat()
    pred_path = PRED / f"predictions_{ts}.json"
    dump_json(pred_path, preds)
    pred_digest = sha256_file(pred_path)
    print(f"[pin] predictions: {pred_path.name} sha256={pred_digest}")

    # ---- 2. build + transpile ----
    from qiskit import qpy, transpile
    arms = arm_list()
    print(f"[build] {len(arms)} arms")
    if DRY:
        backend = None
    else:
        service = get_service()
        backend, snap_path = snapshot(service)
        print(f"[snapshot] {snap_path.name}")

    meta = {"script": "tt01_submit.py",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "predictions_file": pred_path.name,
            "predictions_sha256": pred_digest,
            "optimization_level": OPT_LEVEL, "backend": BACKEND_NAME,
            "circuits": []}
    pubs = []
    for a in arms:
        from tt_common import D_OF, LINE
        d = D_OF[a["code"]]
        qc = build_rep_circuit_inj(d, a["basis"], 4, inject=a["inject"])
        seed = stable_seed("INJTT", a["code"], a["basis"], a["name"], 0)
        name = f"{a['code'].lower()}_{a['basis'].lower()}_{a['name']}"
        if backend is not None:
            tqc = transpile(qc, backend=backend, optimization_level=OPT_LEVEL,
                            initial_layout=LINE[a["code"]], seed_transpiler=seed)
        else:
            tqc = qc
        qpy_path = CIRC / f"{name}.qpy"
        if backend is not None:
            with open(qpy_path, "wb") as f:
                qpy.dump(tqc, f)
        entry = {k: a[k] for k in ("code", "basis", "name", "kind", "shots")}
        if a["kind"] == "stoch":
            entry.update(p=a["p"], variant=a["variant"], mask=a["mask"])
        entry.update(seed_transpiler=seed, file=f"circuits/{name}.qpy",
                     sha256=canonical_circuit_digest(tqc),
                     depth=tqc.depth())
        if backend is not None:
            entry["qpy_sha256"] = sha256_file(qpy_path)
        meta["circuits"].append(entry)
        pubs.append((a, tqc))
    dump_json(CIRC / "circuits_metadata_theorytest.json", meta)
    print(f"[build] metadata digest-ready; {len(pubs)} circuits")
    if DRY:
        print("[dry-run] no submission."); return

    # ---- 3. submit: 4 jobs (det/stoch x Z/X) ----
    from qiskit_ibm_runtime import SamplerV2
    sampler = SamplerV2(mode=backend)
    jobs = []
    groups = {}
    for a, tqc in pubs:
        key = (a["kind"], a["basis"])
        groups.setdefault(key, []).append((a, tqc))
    for (kind, basis), items in sorted(groups.items()):
        shots = SHOTS_DET if kind == "det" else SHOTS_STOCH
        job = sampler.run([t for _, t in items], shots=shots)
        jid = job.job_id()
        for a, _ in items:
            jobs.append({"job_id": jid, "group": f"{kind}_{basis.lower()}",
                         "code": a["code"], "basis": a["basis"],
                         "name": a["name"], "shots": shots})
        print(f"[submit] {kind}_{basis.lower()}: job {jid}, "
              f"{len(items)} pubs x {shots} shots")
    dump_json(RES / "theorytest_jobs.json", {
        "submitted_utc": datetime.now(timezone.utc).isoformat(),
        "predictions_sha256": pred_digest, "jobs": jobs})
    print("[done] job IDs saved to results/theorytest_jobs.json")


if __name__ == "__main__":
    main()
