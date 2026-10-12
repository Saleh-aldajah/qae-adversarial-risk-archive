"""
qae_utils.py  —  Shared utilities for the QAE v17 revision archive.

Factors the helpers that were copy-pasted across runner scripts in v16
(audit finding: helper duplication) into one module:
  - stable_seed()          deterministic SHA-256-derived 32-bit seed
  - wilson95()             two-sided Wilson score 95% CI
  - wilson_one_sided_upper()  one-sided 95% upper bound (zero-failure rows)
  - build_lookup()         radius-r syndrome->correction lookup table
  - mc_row()               provenance row dict (code/decoder/p/fails/trials/
                           seed/sha256(Hx)/sha256(Hz)) per archive scheme

Exact seed formulas (five v16 contexts, extended for v17):
  single-round BP+OSD / MWPM-DEM : stable_seed(code, decoder, p)
  single-round UF-BFS            : stable_seed('UF', code, p)
  repeated-cycle BP+OSD          : stable_seed('RC', code, p, rounds)
  hardware ablations             : stable_seed('ABL', condition, p_base)
  three-backend comparison       : stable_seed('HW3', backend, p)
  v17 extensions (new contexts, same construction):
  E0 correctability sampling     : stable_seed('E0', code, decoder, w)
  E1 rare-event BP+OSD           : stable_seed('E1', code, p)
  E2 UF-BFS BB288                : stable_seed('UF', 'BB288', p)   [same formula as UF]
  E3 adaptive repeated-cycle     : stable_seed('E3', code, p, rounds, batch)
  E4 robustness sweep            : stable_seed('E4', osd_order, ms_scale, p)
  E5 independent cross-check     : stable_seed('E5X', code, p) + 10**9  [fresh stream]
  E6 BP-guided matching          : stable_seed('E6', code, p)

Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
import csv
import hashlib
import itertools
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data"


def stable_seed(*args):
    """Deterministic 32-bit seed: first 4 bytes of SHA-256 of the
    '|'-joined context string, big-endian. PYTHONHASHSEED-independent."""
    key = "|".join(str(a) for a in args).encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:4], 'big')


def wilson95(k, n):
    """Two-sided Wilson score interval, z = 1.96 (95%)."""
    if n == 0:
        return 0., 1.
    z = 1.96
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0., c - m), min(1., c + m)


def wilson_one_sided_upper(k, n, z=1.6448536269514722):
    """One-sided 95% Wilson upper bound (used when k == 0).
    For k=0, n=10^6 this gives ~3.0e-6 (rule-of-three, 3/n);
    with z=1.96 it gives ~3.84e-6."""
    if n == 0:
        return 1.
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return min(1., c + m)


def build_lookup(col_syns, n, radius):
    """Minimum-weight syndrome->correction lookup over all patterns of
    weight <= radius. Used for the radius-2 certified decoder."""
    table = {0: 0}
    for w in range(1, radius + 1):
        for comb in itertools.combinations(range(n), w):
            syn = mask = 0
            for j in comb:
                syn ^= col_syns[j]
                mask |= 1 << j
            if syn not in table or bin(table[syn]).count('1') > bin(mask).count('1'):
                table[syn] = mask
    return table


def mc_row(exp, code, cname, decoder, rounds, p, trials, failures, seed,
           lfr_digits=6):
    """Provenance row following the archive scheme: every Monte-Carlo row
    carries code/decoder/p/fails/trials/seed/sha256(Hx)/sha256(Hz)."""
    lo, hi = wilson95(failures, trials)
    return dict(exp=exp, code=cname, decoder=decoder, rounds=rounds,
                p=p, trials=trials, failures=failures,
                lfr=round(failures / trials, lfr_digits),
                ci_lo=round(lo, lfr_digits), ci_hi=round(hi, lfr_digits),
                seed=seed, hx_sha256=code['hx_sha'], hz_sha256=code['hz_sha'])


def write_csv(fname, rows, fieldnames=None):
    OUT.mkdir(exist_ok=True)
    fn = fieldnames or list(rows[0].keys())
    with open(OUT / fname, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        w.writerows(rows)
    print(f"Saved {fname}  ({len(rows)} rows)")
