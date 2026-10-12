"""
validate_seed_consistency.py - checks that archived CSV seed fields match
SHA-256 stable_seed() rules used by the runner scripts.

Exact seed formulas (B4 fix - all contexts documented):
  single-round BP+OSD / MWPM-DEM : stable_seed(code, decoder, p)
  single-round UF-BFS            : stable_seed('UF', code, p)
  repeated-cycle BP+OSD (v16)    : stable_seed('RC', code, p, rounds)
  hardware ablations             : stable_seed('ABL', condition, p_base)
  three-backend comparison       : stable_seed('HW3', backend, p)
  E0 correctability (exact w<=2) : stable_seed('E0', code, 'exact', w)
  E0 correctability (w=3 sample) : stable_seed('E0', code, 'sample', 3)
  E1 rare-event BP+OSD           : stable_seed('E1', code, p)
  E3 adaptive repeated-cycle     : stable_seed('E3', code, p, rounds, batch)
  E4 robustness sweep            : stable_seed('E4', osd_order, ms_scale, p)
  E5 independent cross-check     : (stable_seed('E5X', code, p) + 10**9) % 2**32
  E6 BP-guided matching          : stable_seed('E6', code, p)

v24 families (second repair round):
  RC fixed ladder v24            : stable_seed('RCv24', code, p, rounds)
  E3 adaptive v24                : stable_seed('E3v24', code, p, rounds, batch)
                                   (CSV 'seed' = batch 0; batch_seeds col i =
                                   batch i)
  injection-boundary v24         : stable_seed('IBDv24', 'trials')  (constant
                                   per-row replay seed; probe/w3 RNG streams
                                   are frozen in ibd_v24_freeze.json)
  REP exact stratification       : stable_seed('REP-EXACT', d)
  WSC circuit arm (comparator)   : stable_seed('WSC', p, rounds)

Exits 0 on pass and 1 on any mismatch.
"""
from __future__ import annotations
import csv, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from qae_utils import stable_seed


def check_file(rel: str, seed_args, skip=None):
    path = ROOT / rel
    errors = []
    with path.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    for idx, row in enumerate(rows, 1):
        if skip and skip(row):
            continue
        exp = int(row["seed"])
        got = stable_seed(*seed_args(row))
        if got != exp:
            errors.append((rel, idx, exp, got, row))
    return len(rows), errors


checks = [
    ("data/single_round_bposd_mwpm_dem.csv",
     lambda r: (r["code"], r["decoder"], float(r["p"])), None),
    ("data/single_round_all_codes.csv",
     lambda r: (r["code"], r["decoder"], float(r["p"])), None),
    ("data/single_round_uf_decoder.csv",
     lambda r: ("UF", r["code"], float(r["p"])), None),
    ("data/single_round_uf_bb288.csv",
     lambda r: ("UF", r["code"], float(r["p"])), None),
    ("data/repeated_cycle_bposd.csv",
     lambda r: ("RC", r["code"], float(r["p"]), int(r["rounds"])), None),
    ("data/repeated_cycle_bb288_bposd.csv",
     lambda r: ("RC", r["code"], float(r["p"]), int(r["rounds"])), None),
    ("data/repeated_cycle_all_codes.csv",
     lambda r: ("RC", r["code"], float(r["p"]), int(r["rounds"])), None),
    ("data/hardware_ablations.csv",
     lambda r: ("ABL", r["condition"], float(r["p_base"])), None),
    ("data/hardware_three_condition_comparison.csv",
     lambda r: ("HW3", r["backend"], float(r["p"])), None),
    # ── v17 extension experiments ──
    ("data/correctability_by_weight.csv",
     lambda r: ("E0", r["code"],
                "sample" if int(r["weight"]) == 3 else "exact",
                int(r["weight"])), None),
    ("data/rare_event_bposd.csv",
     lambda r: ("E1", r["code"], float(r["p"])), None),
    ("data/repeated_cycle_adaptive_bb72.csv",
     lambda r: ("E3", r["code"], float(r["p"]), int(r["rounds"]), 0), None),
    ("data/repeated_cycle_adaptive_bb144.csv",
     lambda r: ("E3", r["code"], float(r["p"]), int(r["rounds"]), 0), None),
    ("data/repeated_cycle_adaptive_bb288.csv",
     lambda r: ("E3", r["code"], float(r["p"]), int(r["rounds"]), 0), None),
    ("data/robustness_sweep_bb72.csv",
     lambda r: ("E4", int(r["osd_order"]), float(r["ms_scale"]), float(r["p"])), None),
    ("data/bp_guided_matching_bb72.csv",
     lambda r: ("E6", r["code"], float(r["p"])), None),
    # ── v21: p=0.010 adaptive extension ──
    ("data/repeated_cycle_adaptive_p010_bb72.csv",
     lambda r: ("E3", r["code"], float(r["p"]), int(r["rounds"]), 0), None),
    ("data/repeated_cycle_adaptive_p010_bb144.csv",
     lambda r: ("E3", r["code"], float(r["p"]), int(r["rounds"]), 0), None),
    ("data/repeated_cycle_adaptive_p010_bb288.csv",
     lambda r: ("E3", r["code"], float(r["p"]), int(r["rounds"]), 0), None),
    # ── v24: fixed RC ladder (aligned priors) ──
    ("data/repeated_cycle_bposd_v24.csv",
     lambda r: ("RCv24", r["code"], float(r["p"]), int(r["rounds"])), None),
    ("data/repeated_cycle_bb288_bposd_v24.csv",
     lambda r: ("RCv24", r["code"], float(r["p"]), int(r["rounds"])), None),
    ("data/repeated_cycle_all_codes_v24.csv",
     lambda r: ("RCv24", r["code"], float(r["p"]), int(r["rounds"])), None),
    # ── v24: injection-boundary decoders (constant replay seed) ──
    ("data/injection_boundary_decoders_v24.csv",
     lambda r: ("IBDv24", "trials"), None),
    # ── v24: REP exact stratification ──
    ("data/rep_exact_lfr_v24.csv",
     lambda r: ("REP-EXACT", int(r["d"])), None),
    ("data/rep_exact_masks_v24.csv",
     lambda r: ("REP-EXACT", int(r["d"])), None),
    # ── v24/v25: WSC circuit arm (comparator tree) ──
    ("../comparator/results/wsc_circuit.csv",
     lambda r: ("WSC", float(r["p"]), int(r["rounds"])), None),
]


def check_e3_v24():
    """E3v24 adaptive ladder: CSV 'seed' must equal batch-0 seed and every
    entry of the semicolon-joined batch_seeds column must equal
    stable_seed('E3v24', code, p, rounds, batch_idx)."""
    errors = []
    n = 0
    for tag in ("bb72", "bb144", "bb288"):
        for prefix, ctx in (("data/repeated_cycle_adaptive_", "E3v24"),
                            ("data/repeated_cycle_adaptive_p010_",
                             "E3v24p010")):
            rel = f"{prefix}{tag}_v24.csv"
            path = ROOT / rel
            if not path.exists():
                errors.append((rel, 0, 0, 0, {"error": "missing file"}))
                continue
            with path.open(newline="") as fh:
                for idx, row in enumerate(csv.DictReader(fh), 1):
                    n += 1
                    args = (row["code"], float(row["p"]), int(row["rounds"]))
                    got0 = stable_seed(ctx, *args, 0)
                    if int(row["seed"]) != got0:
                        errors.append((rel, idx, int(row["seed"]), got0, row))
                        continue
                    bs = row.get("batch_seeds") or ""
                    for bi, tok in enumerate(bs.split(";")):
                        if not tok:
                            continue
                        got = stable_seed(ctx, *args, bi)
                        if int(tok) != got:
                            errors.append((rel, idx, int(tok), got,
                                           {"batch": bi, **row}))
                            break
    return n, errors


def check_e5():
    """E5 fresh rows: seed = (stable_seed('E5X', code, p) + 10**9) % 2**32.
    Archive reference rows keep their original v16 seeds (checked via the
    single_round_all_codes.csv rule above) and are skipped here."""
    errors = []
    with (ROOT / "data/crosscheck_e5.csv").open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    for idx, row in enumerate(rows, 1):
        if row["path"] != "fresh":
            continue
        exp = int(row["seed"])
        got = (stable_seed("E5X", row["code"], float(row["p"])) + 10**9) % 2**32
        if got != exp:
            errors.append(("data/crosscheck_e5.csv", idx, exp, got, row))
    return len(rows), errors


n_rows = 0
all_errors = []
for rel, args, skip in checks:
    try:
        rows, errors = check_file(rel, args, skip)
    except FileNotFoundError:
        print(f"MISSING: {rel}")
        all_errors.append((rel, 0, 0, 0, {}))
        continue
    n_rows += rows
    all_errors.extend(errors)
    print(f"{rel}: {rows} rows checked, {len(errors)} mismatches")

rows, errors = check_e5()
n_rows += rows
all_errors.extend(errors)
print(f"data/crosscheck_e5.csv: {rows} rows checked, {len(errors)} mismatches")

rows, errors = check_e3_v24()
n_rows += rows
all_errors.extend(errors)
print(f"E3v24 adaptive ladder (incl. batch_seeds): {rows} rows checked, "
      f"{len(errors)} mismatches")

if all_errors:
    print("\nSEED VERIFICATION FAILED")
    for rel, idx, exp, got, row in all_errors[:20]:
        print(f"  {rel}:{idx}: expected {exp}, stable_seed() gives {got}, row={row}")
    sys.exit(1)

print(f"\nAll seed fields verified across {n_rows} rows.")
sys.exit(0)
