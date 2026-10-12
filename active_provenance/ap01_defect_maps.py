#!/usr/bin/env python
"""ap01_defect_maps.py — Syndrome-localized defect maps + metrology-informed
line selection (Stage-10 "active provenance", offline leg).

Inputs (all archived, digest-bound):
  * ibm_demo/counts/counts_rep{3,5}_{z,x}_r4_10k_online.json   (Aug-11, 10k)
  * ibm_demo/counts/counts_rep{3,5}_z_r4_drift_online.json,
    counts_rep3_x_r4_drift_online.json                          (Aug-27, 2k)
  * ibm_demo/results/ibm_demo_readout_check.csv                 (Aug-27, measured)
  * ibm_demo/backend_snapshots/ibm_marrakesh_snapshot_20260827T165954Z.json

Outputs (active_provenance/):
  * results/ap_defect_maps.csv        per-job x per-ancilla x per-round
                                      detection rates + per-data final flips
  * results/ap_line_selection.csv     all candidate windows scored by
                                      snapshot-only and metrology-augmented
                                      costs (the selection record)
  * results/ap_defect_maps.json       machine-readable copy + input digests
  * figures/ap_f1_defect_map.pdf/.png per-ancilla detection-rate heatmap

Bit convention (ibm_demo_common.build_rep_circuit): clbit t*(d-1)+c = ancilla
c round t; clbit r*(d-1)+j = final data j. Counts bitstrings are big-endian
strings (rightmost char = clbit 0).

Physical mapping on the ORIGINAL lines: REP3 line [0,1,2,3,4],
REP5 line [0..8]; ancilla c -> line[2c+1], data j -> line[2j].
"""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DEMO = HERE.parent / "ibm_demo"
RESULTS = HERE / "results"
FIGS = HERE / "figures"
RESULTS.mkdir(exist_ok=True)
FIGS.mkdir(exist_ok=True)

LINES = {3: [0, 1, 2, 3, 4], 5: [0, 1, 2, 3, 4, 5, 6, 7, 8]}
W_IDLE_NS = 5404.0  # inter-round window (2684 ns meas + 2720 ns reset), CALIB_V2
PATH = list(range(16)) + [19, 35, 34, 33, 32]  # known SWAP-free path (REP9/11)

JOBS = [
    ("counts_rep3_z_r4_10k_online.json", 3, 4, "Z", "2026-08-11", 10000),
    ("counts_rep3_x_r4_10k_online.json", 3, 4, "X", "2026-08-11", 10000),
    ("counts_rep5_z_r4_10k_online.json", 5, 4, "Z", "2026-08-11", 10000),
    ("counts_rep5_x_r4_10k_online.json", 5, 4, "X", "2026-08-11", 10000),
    ("counts_rep3_z_r4_drift_online.json", 3, 4, "Z", "2026-08-27", 2000),
    ("counts_rep3_x_r4_drift_online.json", 3, 4, "X", "2026-08-27", 2000),
    ("counts_rep5_z_r4_drift_online.json", 5, 4, "Z", "2026-08-27", 2000),
]


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def parse_rep_counts(counts, d, rounds):
    nanc = d - 1
    shots = sum(counts.values())
    det = np.zeros((rounds, nanc))
    anc1 = np.zeros((rounds, nanc))
    dataflip = np.zeros(d)
    for bs, k in counts.items():
        bits = bs[::-1]
        a = np.array([[int(bits[t * nanc + c]) for c in range(nanc)]
                      for t in range(rounds)])
        anc1 += a * k
        dets = a.copy()
        dets[1:] = a[1:] ^ a[:-1]
        det += dets * k
        f = np.array([int(bits[rounds * nanc + j]) for j in range(d)])
        dataflip += f * k
    return det / shots, anc1 / shots, dataflip / shots, shots


def main():
    input_digests = {}
    rows = []
    maps = {}
    for fn, d, r, basis, day, shots_req in JOBS:
        p = DEMO / "counts" / fn
        input_digests[f"counts/{fn}"] = sha256_file(p)
        cj = json.loads(p.read_text())
        det, anc1, dflip, shots = parse_rep_counts(cj["counts"], d, r)
        line = LINES[d]
        tag = f"REP{d}-{basis}-r{r}-{day}"
        maps[tag] = {"det": det.tolist(), "anc1": anc1.tolist(),
                     "dflip": dflip.tolist(), "shots": shots,
                     "job_id": cj["job_id"]}
        for c in range(d - 1):
            for t in range(r):
                rows.append({
                    "config": tag, "basis": basis, "d": d, "day": day,
                    "element": f"anc{c}", "phys_qubit": line[2 * c + 1],
                    "round": t, "rate": f"{det[t, c]:.6f}",
                    "kind": "detection"})
        for c in range(d - 1):
            rows.append({
                "config": tag, "basis": basis, "d": d, "day": day,
                "element": f"anc{c}", "phys_qubit": line[2 * c + 1],
                "round": "all", "rate": f"{det[:, c].mean():.6f}",
                "kind": "detection_marginal"})
        for j in range(d):
            rows.append({
                "config": tag, "basis": basis, "d": d, "day": day,
                "element": f"data{j}", "phys_qubit": line[2 * j],
                "round": "final", "rate": f"{dflip[j]:.6f}",
                "kind": "data_flip"})

    # ---- line selection ------------------------------------------------
    snap_path = DEMO / "backend_snapshots" / \
        "ibm_marrakesh_snapshot_20260827T165954Z.json"
    input_digests["backend_snapshots/" + snap_path.name] = sha256_file(snap_path)
    snap = json.loads(snap_path.read_text())
    props = snap["properties"]
    qub, gates = props["qubits"], props["gates"]

    def qprop(q, name):
        for dd in qub[q]:
            if dd["name"] == name:
                return dd["value"]

    def cze(a, b):
        for g in gates:
            if g.get("qubits") == [a, b] and g["gate"] == "cz":
                for pp in g["parameters"]:
                    if pp["name"] == "gate_error":
                        return pp["value"]

    rc_path = DEMO / "results" / "ibm_demo_readout_check.csv"
    input_digests["results/ibm_demo_readout_check.csv"] = sha256_file(rc_path)
    rc = {}
    with open(rc_path) as f:
        for row in csv.DictReader(f):
            rc[int(row["qubit"])] = float(row["meas_sym"])

    def idle_cost(q):
        return W_IDLE_NS / 1000.0 * (1.0 / qprop(q, "T1") + 1.0 / qprop(q, "T2"))

    def ro_snap(q):
        return (qprop(q, "prob_meas1_prep0") + qprop(q, "prob_meas0_prep1")) / 2.0

    def score(line, use_measured):
        s = 0.0
        for q in line:
            ro = rc[q] if (use_measured and q in rc) else ro_snap(q)
            s += ro + idle_cost(q)
        for a, b in zip(line[:-1], line[1:]):
            s += cze(a, b)
        return s

    sel_rows = []
    for n in (5, 9):
        for i in range(len(PATH) - n + 1):
            w = PATH[i:i + n]
            sel_rows.append({
                "length": n, "line": "-".join(map(str, w)),
                "score_metrology": f"{score(w, True):.6f}",
                "score_snapshot_only": f"{score(w, False):.6f}",
                "contains_q1": int(1 in w), "contains_q0": int(0 in w),
                "is_original": int(w == LINES[3] or w == LINES[5])})
        sel_rows_sorted = sorted([r for r in sel_rows if r["length"] == n],
                                 key=lambda r: float(r["score_metrology"]))
        for rank, r in enumerate(sel_rows_sorted):
            r["rank_metrology"] = rank

    # ---- write outputs --------------------------------------------------
    with open(RESULTS / "ap_defect_maps.csv", "w", newline="") as f:
        wcsv = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wcsv.writeheader()
        wcsv.writerows(rows)
    with open(RESULTS / "ap_line_selection.csv", "w", newline="") as f:
        wcsv = csv.DictWriter(f, fieldnames=list(sel_rows[0].keys()))
        wcsv.writeheader()
        wcsv.writerows(sel_rows)
    (RESULTS / "ap_defect_maps.json").write_text(json.dumps(
        {"script": "ap01_defect_maps.py", "maps": maps,
         "line_selection": sel_rows, "input_digests": input_digests},
        indent=1))

    # ---- figure ----------------------------------------------------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(7.0, 4.6))
    panels = [("REP3-Z-r4-2026-08-11", "REP3 Z"), ("REP3-X-r4-2026-08-11", "REP3 X"),
              ("REP5-Z-r4-2026-08-11", "REP5 Z"), ("REP5-X-r4-2026-08-11", "REP5 X")]
    vmax = 0.05
    for ax, (tag, title) in zip(axes.flat, panels):
        det = np.array(maps[tag]["det"]).T  # anc x round
        im = ax.imshow(det, aspect="auto", cmap="inferno", vmin=0, vmax=vmax)
        line = LINES[3 if "REP3" in tag else 5]
        ax.set_yticks(range(det.shape[0]))
        ax.set_yticklabels([f"anc{c} (q{line[2*c+1]})" for c in range(det.shape[0])],
                           fontsize=7)
        ax.set_xticks(range(det.shape[1]))
        ax.set_xlabel("round $t$", fontsize=8)
        ax.set_title(f"{title}, r=4, 10k shots", fontsize=9)
        for c in range(det.shape[0]):
            for t in range(det.shape[1]):
                ax.text(t, c, f"{det[c, t]:.3f}", ha="center", va="center",
                        fontsize=6, color="w" if det[c, t] < vmax / 2 else "k")
    fig.suptitle("Per-ancilla detection-event rates on ibm_marrakesh (physical qubit in parentheses)",
                 fontsize=9)
    fig.tight_layout(rect=[0, 0, 0.93, 0.95])
    cax = fig.add_axes([0.94, 0.12, 0.015, 0.72])
    cb = fig.colorbar(im, cax=cax, ticks=[0, 0.01, 0.02, 0.03, 0.04, 0.05])
    cb.set_label("detection rate", fontsize=8)
    cb.ax.tick_params(labelsize=7)
    fig.savefig(FIGS / "ap_f1_defect_map.pdf")
    fig.savefig(FIGS / "ap_f1_defect_map.png", dpi=200)
    print("wrote", RESULTS / "ap_defect_maps.csv", RESULTS / "ap_line_selection.csv",
          FIGS / "ap_f1_defect_map.pdf", sep="\n  ")

    # console summary of the decision
    for n, orig in ((5, LINES[3]), (9, LINES[5])):
        rs = sorted([r for r in sel_rows if r["length"] == n],
                    key=lambda r: float(r["score_metrology"]))
        best = rs[0]
        o = next(r for r in rs if r["is_original"])
        print(f"n={n}: best={best['line']} (metro {best['score_metrology']}) | "
              f"original rank {o['rank_metrology']+1}/{len(rs)} "
              f"(metro {o['score_metrology']}, snapshot-only {o['score_snapshot_only']})")


if __name__ == "__main__":
    main()
