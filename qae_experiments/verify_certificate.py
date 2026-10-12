"""
verify_certificate.py  —  Self-contained BB72 finite-instance certificate.

Runs entirely from the local archive directory using only bb_codes.py
and decoders.py.  No installed packages required beyond numpy.
Exits 0 on full pass, 1 on any failure.

Obligations verified
--------------------
O1  Commutation: HX @ HZ^T = 0 over GF(2)
O2  Dimension:   k = n - rank(HX) - rank(HZ) = 12
O3  d >= 6:      Meet-in-the-middle exhaustive search through weight 5.
                 Confirms no nontrivial zero-syndrome vector of weight <=5
                 exists in either CSS component.
O4  t=2 radius:  All 2,629 = sum_{w=0}^{2} C(72,w) weight-<=2 patterns
                 corrected by radius-2 lookup; zero failures.
O5  d = 6 exact: Exhaustive MITM 3+3 enumeration of all C(72,3)=59,640
                 triples per sector; every weight-6 kernel vector splits
                 into two disjoint triples of equal syndrome, so the
                 enumeration is complete.  Exhibits 84 + 84 nontrivial
                 weight-6 logicals, each verified syndrome-zero, outside
                 the opposite row space, and anticommuting with at least
                 one opposite-sector weight-6 logical.  Combined with O3b
                 (no weight <=5 logicals) this certifies d = 6 exactly.

Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
import sys
import json
import itertools
import hashlib
from pathlib import Path

# ── Portable path setup ────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import numpy as np

# Import only from local archive files
from bb_codes import BB72, gf2_rank, gf2_rref, in_rowspace, syn_from_mask

code  = BB72
n     = code['n']
n2    = n // 2
HX    = code['HX']
HZ    = code['HZ']
errors = []

print("BB72 Certificate Verification  (self-contained, archive-local)")
print("="*60)

# ──────────────────────────────────────────────────────────────────────────
# O1  Commutation
# ──────────────────────────────────────────────────────────────────────────
comm = bool(np.all(((HX @ HZ.T) & 1) == 0))
print(f"O1  Commutation HX @ HZ^T = 0 (mod 2):  {'PASS' if comm else 'FAIL'}")
if not comm:
    errors.append("O1: commutation failed")

# ──────────────────────────────────────────────────────────────────────────
# O2  Dimension
# ──────────────────────────────────────────────────────────────────────────
k_val = n - code['rx'] - code['rz']
print(f"O2  Dimension k = {n} - {code['rx']} - {code['rz']} = {k_val}: "
      f"{'PASS' if k_val == 12 else 'FAIL'}")
if k_val != 12:
    errors.append(f"O2: k={k_val}, expected 12")

# ──────────────────────────────────────────────────────────────────────────
# O3  Distance lower bound  d >= 6
#     Meet-in-the-middle exhaustive search, split <= 2 / <= 3
# ──────────────────────────────────────────────────────────────────────────
EXP_HX_SHA = ("7ab0973bfd02e399d69728d26e67dbfa"
               "0e95bbc6ad2c5cf8bf309d667244a5a8")
EXP_HZ_SHA = ("267f345c09710ec0cfad1e49e0786b26"
               "36ab052fbfb660e5a76ae9919ba22614")

actual_hx = hashlib.sha256(HX.astype(np.uint8).tobytes()).hexdigest()
actual_hz = hashlib.sha256(HZ.astype(np.uint8).tobytes()).hexdigest()
sha_ok = (actual_hx == EXP_HX_SHA and actual_hz == EXP_HZ_SHA)
print(f"O3a SHA-256 matrix identity:             {'PASS' if sha_ok else 'FAIL'}")
if not sha_ok:
    errors.append("O3a: SHA-256 mismatch")
    print(f"    HX expected: {EXP_HX_SHA}")
    print(f"    HX actual:   {actual_hx}")

def mitm_distance_lb(H_cols, H_rref, H_pivots, n, left_max, right_max):
    """
    Meet-in-the-middle enumeration.
    Returns (witnesses, left_count, right_count).
    witnesses is a list of nontrivial zero-syndrome vectors found.
    """
    left_by_syn: dict = {}
    left_count = right_count = 0
    witnesses = []

    # Build left table: all patterns of weight <= left_max
    for w in range(left_max + 1):
        for comb in itertools.combinations(range(n), w):
            syn = mask = 0
            for j in comb:
                syn ^= H_cols[j]
                mask |= 1 << j
            left_by_syn.setdefault(syn, []).append(mask)
            left_count += 1

    # Probe right side: all patterns of weight <= right_max
    seen = set()
    for w in range(right_max + 1):
        for comb in itertools.combinations(range(n), w):
            syn = rmask = 0
            for j in comb:
                syn  ^= H_cols[j]
                rmask |= 1 << j
            right_count += 1
            for lmask in left_by_syn.get(syn, []):
                if lmask & rmask:            # overlapping support — skip
                    continue
                full = lmask | rmask
                wt   = bin(full).count('1')
                if wt == 0 or full in seen:
                    continue
                seen.add(full)
                vec = np.array([(full >> i) & 1 for i in range(n)],
                               dtype=np.uint8)
                if not in_rowspace(vec, H_rref, H_pivots):
                    witnesses.append({
                        "weight":  wt,
                        "support": [i for i in range(n) if (full >> i) & 1],
                    })
        if witnesses:
            break

    return witnesses, left_count, right_count

# Compute RREF for stabiliser row spaces (for nontrivial logical check)
HX_rref, HX_pivots = gf2_rref(HX)
HZ_rref, HZ_pivots = gf2_rref(HZ)

# Z-component: look for nontrivial X-logicals (zero HX syndrome,
#              not in row(HZ))
# X-component: look for nontrivial Z-logicals (zero HZ syndrome,
#              not in row(HX))
left_max  = 2   # enumerate all weight <= 2 on left
right_max = 3   # enumerate all weight <= 3 on right  => total <=5 checked

z_witnesses, z_left, z_right = mitm_distance_lb(
    code['hx_cols'], HZ_rref, HZ_pivots, n, left_max, right_max)
x_witnesses, x_left, x_right = mitm_distance_lb(
    code['hz_cols'], HX_rref, HX_pivots, n, left_max, right_max)

d_pass = (len(z_witnesses) == 0 and len(x_witnesses) == 0)
print(f"O3b d>=6 MitM (Z-comp): left={z_left:,}, right={z_right:,}, "
      f"witnesses={len(z_witnesses)}:  {'PASS' if not z_witnesses else 'FAIL'}")
print(f"O3b d>=6 MitM (X-comp): left={x_left:,}, right={x_right:,}, "
      f"witnesses={len(x_witnesses)}:  {'PASS' if not x_witnesses else 'FAIL'}")
if not d_pass:
    errors.append(f"O3b: {len(z_witnesses)+len(x_witnesses)} nontrivial witnesses found")

# ──────────────────────────────────────────────────────────────────────────
# O4  Exhaustive radius-2 correctability
# ──────────────────────────────────────────────────────────────────────────

# Build radius-2 lookup table from bb_codes data (no external package needed)
def build_lookup(col_syns, n, radius):
    table = {0: 0}
    for w in range(1, radius + 1):
        for comb in itertools.combinations(range(n), w):
            syn = mask = 0
            for j in comb:
                syn  ^= col_syns[j]
                mask |= 1 << j
            wt = bin(mask).count('1')
            if syn not in table or bin(table[syn]).count('1') > wt:
                table[syn] = mask
    return table

lookup_z = build_lookup(code['hx_cols'], n, 2)
lookup_x = build_lookup(code['hz_cols'], n, 2)

fail_count = patterns = 0
for w in range(3):                        # weights 0, 1, 2
    for bits in itertools.combinations(range(n), w):
        mask = sum(1 << j for j in bits)
        sz   = syn_from_mask(mask, code['hx_cols'])
        sx   = syn_from_mask(mask, code['hz_cols'])
        cz   = lookup_z.get(sz, 0)
        cx   = lookup_x.get(sx, 0)
        # Residual must be in the respective stabiliser row space
        rz   = mask ^ cz
        rx   = mask ^ cx
        vz   = np.array([((rz >> i) & 1) for i in range(n)], dtype=np.uint8)
        vx   = np.array([((rx >> i) & 1) for i in range(n)], dtype=np.uint8)
        if not (in_rowspace(vz, HZ_rref, HZ_pivots) and
                in_rowspace(vx, HX_rref, HX_pivots)):
            fail_count += 1
        patterns += 1

print(f"O4  Radius-2 correctability ({patterns:,} patterns):  "
      f"{'PASS' if fail_count == 0 else f'FAIL ({fail_count} failures)'}")
if fail_count > 0:
    errors.append(f"O4: {fail_count} correctability failures")

# ──────────────────────────────────────────────────────────────────────────
# O5  Exact distance  d = 6  (exhaustive weight-6 enumeration)
#     MITM 3+3: group all C(72,3) triples by syndrome; any weight-6 kernel
#     vector is a disjoint pair of triples with equal syndrome, so grouping
#     finds ALL weight-6 kernel elements.  Rank-test against the opposite
#     row space isolates the nontrivial logicals; each must anticommute
#     with at least one opposite-sector weight-6 logical.
# ──────────────────────────────────────────────────────────────────────────
EXP_O5 = {
    "z_candidates": 120, "x_candidates": 120,
    "z_nontrivial": 84,  "x_nontrivial": 84,
    "z_lex_first": [0, 1, 2, 3, 20, 22],
    "x_lex_first": [0, 3, 6, 12, 27, 30],
    "lex_first_partners": 30,
    "anticommuting_pairs": 2592,
}

def weight6_kernel_logicals(col_syns, opp_rref, opp_pivots, n):
    """Return (candidates, nontrivial) as sorted lists of 6-tuples."""
    by_syn: dict = {}
    for comb in itertools.combinations(range(n), 3):
        syn = col_syns[comb[0]] ^ col_syns[comb[1]] ^ col_syns[comb[2]]
        by_syn.setdefault(syn, []).append(comb)
    cands = set()
    for syn, triples in by_syn.items():
        for i in range(len(triples)):
            for j in range(i + 1, len(triples)):
                a, b = triples[i], triples[j]
                if not (set(a) & set(b)):
                    cands.add(tuple(sorted(a + b)))
    cands = sorted(cands)
    nontriv = []
    for c in cands:
        vec = np.array([(1 if i in c else 0) for i in range(n)],
                       dtype=np.uint8)
        if not in_rowspace(vec, opp_rref, opp_pivots):
            nontriv.append(c)
    return cands, nontriv

z_cands6, z_log6 = weight6_kernel_logicals(code['hx_cols'], HZ_rref, HZ_pivots, n)
x_cands6, x_log6 = weight6_kernel_logicals(code['hz_cols'], HX_rref, HX_pivots, n)

# Anticommutation structure: overlap parity between sectors
def _parity(a, b):
    return len(set(a) & set(b)) % 2

anti_pairs = sum(1 for z in z_log6 for x in x_log6 if _parity(z, x))
z_partnered = all(any(_parity(z, x) for x in x_log6) for z in z_log6)
x_partnered = all(any(_parity(z, x) for z in z_log6) for x in x_log6)
z_lex_partners = sum(1 for x in x_log6 if _parity(z_log6[0], x)) if z_log6 else 0

o5_ok = (len(z_cands6) == EXP_O5["z_candidates"] and
         len(x_cands6) == EXP_O5["x_candidates"] and
         len(z_log6)   == EXP_O5["z_nontrivial"] and
         len(x_log6)   == EXP_O5["x_nontrivial"] and
         list(z_log6[0]) == EXP_O5["z_lex_first"] and
         list(x_log6[0]) == EXP_O5["x_lex_first"] and
         z_lex_partners == EXP_O5["lex_first_partners"] and
         anti_pairs == EXP_O5["anticommuting_pairs"] and
         z_partnered and x_partnered)
print(f"O5  d=6 exact (weight-6 enumeration): "
      f"Z-comp {len(z_cands6)} candidates / {len(z_log6)} logicals, "
      f"X-comp {len(x_cands6)} candidates / {len(x_log6)} logicals, "
      f"{anti_pairs} anticommuting pairs:  "
      f"{'PASS' if o5_ok else 'FAIL'}")
if not o5_ok:
    errors.append("O5: weight-6 enumeration mismatch vs pinned values")

# ──────────────────────────────────────────────────────────────────────────
# Save report to data/
# ──────────────────────────────────────────────────────────────────────────
(ROOT / "data").mkdir(exist_ok=True)
report = {
    "code":              "BB72",
    "n": n, "k": k_val,
    "O1_commutation":    comm,
    "O2_dimension_k":    k_val,
    "O3a_hx_sha256":     actual_hx,
    "O3a_hz_sha256":     actual_hz,
    "O3b_method":        "meet-in-the-middle, split <=2 / <=3",
    "O3b_z_left_patterns":  z_left,
    "O3b_z_right_patterns": z_right,
    "O3b_z_witnesses":      z_witnesses,
    "O3b_x_left_patterns":  x_left,
    "O3b_x_right_patterns": x_right,
    "O3b_x_witnesses":      x_witnesses,
    "O3b_distance_lower_bound_pass": d_pass,
    "O4_patterns_checked": patterns,
    "O4_failures":         fail_count,
    "O5_method":           ("exact distance: exhaustive MITM 3+3 enumeration of all "
                            "C(72,3)=59640 triples per sector; every weight-6 kernel "
                            "vector splits into two disjoint triples with equal syndrome, "
                            "so the enumeration is complete; combined with O3b/O4 "
                            "(no weight<=5 logicals) this certifies d=6 exactly"),
    "O5_z_weight6_kernel_candidates": len(z_cands6),
    "O5_x_weight6_kernel_candidates": len(x_cands6),
    "O5_z_nontrivial_logicals":       len(z_log6),
    "O5_x_nontrivial_logicals":       len(x_log6),
    "O5_z_witnesses_weight6":         [list(z) for z in z_log6],
    "O5_x_witnesses_weight6":         [list(x) for x in x_log6],
    "O5_z_lex_first_witness":         list(z_log6[0]) if z_log6 else None,
    "O5_x_lex_first_witness":         list(x_log6[0]) if x_log6 else None,
    "O5_lex_first_anticommuting_partners": z_lex_partners,
    "O5_anticommuting_pairs_total":   anti_pairs,
    "O5_witnesses_verified":          bool(z_partnered and x_partnered),
    "O5_distance_exact":              6 if o5_ok else None,
    "certificate_conclusion":         ("BB72 is a [[72,12,6]] code: d=6 exactly "
                                       "(O3b/O4 exclude d<=5; O5 exhibits 84+84 "
                                       "nontrivial weight-6 logicals)"),
    "all_pass":            len(errors) == 0,
    "errors":              errors,
}
report_path = ROOT / "data" / "bb72_certificate_report.json"
with open(report_path, "w") as f:
    json.dump(report, f, indent=2)
print(f"\nSaved: {report_path.name}")

# ──────────────────────────────────────────────────────────────────────────
# Final result
# ──────────────────────────────────────────────────────────────────────────
if errors:
    print(f"\n{'='*60}")
    print(f"CERTIFICATE FAILED: {errors}")
    sys.exit(1)

print(f"\n{'='*60}")
print("ALL FIVE OBLIGATIONS PASS")
print(f"  d >= 6: confirmed (MitM, {z_left+x_left:,} left + {z_right+x_right:,} right patterns, 0 witnesses)")
print(f"  t = 2:  confirmed (exhaustive, {patterns:,} weight-<=2 patterns, 0 failures)")
print(f"  d = 6:  exact (weight-6 enumeration, {len(z_log6)}+{len(x_log6)} nontrivial logicals)")
sys.exit(0)
