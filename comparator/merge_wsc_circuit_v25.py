#!/usr/bin/env python3
"""merge_wsc_circuit_v25.py — assemble the v25 WS-C circuit-level grid.

Inputs
  * archived v24 corrected point:  results/wsc_circuit.csv in the *archive*
    tree (p = 0.001, circuit_rev = 'v24-corrected-extraction', the pinned v24
    record quoted by the manuscript);
  * per-point v25 outputs:         results/wsc_circuit_v25_p{p}.csv in this
    (working) tree, produced by the restored corrected wsc_circuit_point.py
    (intra-point checkpointed), for p = 0.002 .. 0.012.

Validation (hard failures)
  * every row must carry circuit_rev == 'v24-corrected-extraction' (the v23
    reversed-extraction rows have no such column and are rejected);
  * shots/rounds must match the pinned protocol (20000 / 4);
  * all five decoder rows of a point must share one dem_sha256;
  * each of the seven p values must appear exactly once per decoder.

Output
  results/wsc_circuit_v24.csv in BOTH trees (35 rows), plus a sidecar
  results/wsc_circuit_v24_PROVENANCE.md.

Usage: python merge_wsc_circuit_v25.py
"""
import os, csv, sys, hashlib, collections

HERE = os.path.abspath(os.path.dirname(__file__))
ARCH = os.path.normpath(os.path.join(HERE, '..', 'stage-v21', 'archive',
                                     'comparator'))
REV = 'v24-corrected-extraction'
SHOTS, ROUNDS = 20000, 4
DEC = ['BP+OSD', 'Relay-BP', 'BeliefMatch', 'MWPM-chain', 'MWPM-stim']
GRID = [0.001, 0.002, 0.004, 0.006, 0.008, 0.010, 0.012]


def fail(msg):
    print(f"MERGE FAIL: {msg}")
    sys.exit(1)


def load(path):
    if not os.path.exists(path):
        fail(f"missing {path}")
    return list(csv.DictReader(open(path)))


def check_rows(rows, src):
    out = []
    for r in rows:
        if r.get('circuit_rev') != REV:
            fail(f"{src}: row without circuit_rev={REV!r}: {r.get('p')} "
                 f"{r.get('decoder')}")
        if int(r['shots']) != SHOTS or int(r['rounds']) != ROUNDS:
            fail(f"{src}: protocol mismatch at p={r['p']}: "
                 f"shots={r['shots']} rounds={r['rounds']}")
        out.append(r)
    return out


def main():
    merged = []
    # pinned v24 record: p = 0.001
    arch = check_rows(load(os.path.join(ARCH, 'results', 'wsc_circuit.csv')),
                      'archive wsc_circuit.csv')
    p1 = [r for r in arch if float(r['p']) == 0.001]
    if len(p1) != 5:
        fail(f"archive p=0.001 point must have 5 decoder rows, found {len(p1)}")
    merged.extend(p1)

    # v25 per-point files
    for p in GRID[1:]:
        f = os.path.join(HERE, 'results', f'wsc_circuit_v25_p{p}.csv')
        rows = check_rows(load(f), f)
        rows = [r for r in rows if float(r['p']) == p]
        if len(rows) != 5:
            fail(f"{f}: expected 5 decoder rows, found {len(rows)}")
        dems = {r['dem_sha256'] for r in rows}
        if len(dems) != 1:
            fail(f"{f}: decoder rows disagree on dem_sha256: {dems}")
        merged.extend(rows)

    # grid completeness: 7 p x 5 decoders, unique
    seen = collections.Counter((float(r['p']), r['decoder']) for r in merged)
    for p in GRID:
        for d in DEC:
            if seen[(p, d)] != 1:
                fail(f"grid cell p={p} decoder={d}: count {seen[(p, d)]}")
    if len(merged) != 35:
        fail(f"expected 35 rows, got {len(merged)}")

    merged.sort(key=lambda r: (float(r['p']), DEC.index(r['decoder'])))
    cols = list(merged[0].keys())
    for dest in (os.path.join(HERE, 'results', 'wsc_circuit_v24.csv'),
                 os.path.join(ARCH, 'results', 'wsc_circuit_v24.csv')):
        with open(dest, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(merged)
        print('wrote', dest, f"({len(merged)} rows)")

    prov = os.path.join(HERE, 'results', 'wsc_circuit_v24_PROVENANCE.md')
    with open(prov, 'w') as f:
        f.write("# wsc_circuit_v24.csv — provenance\n\n"
                f"- p=0.001: pinned v24 record (archive results/wsc_circuit.csv,"
                f" exp `wsc_circuit_v24`, circuit_rev `{REV}`), reproduced by"
                f" `wsc_verify.py` (ALL PASS) and by the DEM-hash regression"
                f" (sha256 a80e06f9...).\n"
                "- p=0.002..0.012: v25 campaign, restored corrected"
                " `wsc_circuit_point.py` with intra-point checkpointing;"
                " per-point files results/wsc_circuit_v25_p{p}.csv.\n"
                "- The v23 reversed-extraction rows (working-tree"
                " wsc_circuit.csv dated 2026-08-28, identical to"
                " wsc_circuit_v23_reversed_extraction_INVALID.csv) were"
                " quarantined under legacy_quarantine/ and are NOT used.\n")
    # quick stdout table
    by = collections.defaultdict(dict)
    for r in merged:
        by[float(r['p'])][r['decoder']] = r
    print("\n p      " + "".join(f"{d:>14s}" for d in DEC))
    for p in GRID:
        print(f"{p:.3f}  " + "".join(
            f"{int(by[p][d]['failures']):>14d}" for d in DEC))


if __name__ == '__main__':
    main()
