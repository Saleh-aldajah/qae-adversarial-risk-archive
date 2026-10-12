#!/usr/bin/env python3
"""gen_wsc_table.py — emit the v25 tab:wsc LaTeX rows + findings numbers.

Reads results/wsc_circuit_v24.csv (merged 7-point grid, 35 rows) when
present; otherwise falls back to results/wsc_circuit.csv (single pinned
p=0.001 point).  Deterministic transcription: no hand-copied numbers.
Also emits the endpoint/category split demanded by the second-round review:
every decoder column reports unconditional failures, and the two
matching-family decoders are further decomposed into coverage failures
(no perfect matching) vs wrong-logical failures.

Usage: python gen_wsc_table.py"""
import os, csv, collections
HERE = os.path.abspath(os.path.dirname(__file__))
MERGED = os.path.join(HERE, 'results', 'wsc_circuit_v24.csv')
SINGLE = os.path.join(HERE, 'results', 'wsc_circuit.csv')
src = MERGED if os.path.exists(MERGED) else SINGLE
rows = list(csv.DictReader(open(src)))
# guard: only corrected-extraction rows may be transcribed
bad = [r for r in rows if r.get('circuit_rev') != 'v24-corrected-extraction']
if bad:
    raise SystemExit(f"refusing to transcribe {len(bad)} rows without "
                     f"circuit_rev=v24-corrected-extraction from {src}")
DEC = ['BP+OSD', 'Relay-BP', 'BeliefMatch', 'MWPM-chain', 'MWPM-stim']
by = collections.defaultdict(dict)
for r in rows:
    by[float(r['p'])][r['decoder']] = r


def cell(r):
    k, n = int(r['failures']), int(r['shots'])
    if k == 0:
        return f"0 ($<$1.50$\\!\\times\\!10^{{-4}}$)"
    return f"{k} ({k/n:.4f})"


def split(r):
    """coverage (no-matching) vs wrong-logical decomposition."""
    k = int(r['failures'])
    nm = int(r['no_matching'])
    return nm, k - nm


print(f"% --- tab:wsc rows (generated from {os.path.basename(src)}) ---")
for p in sorted(by):
    cells = [cell(by[p][d]) for d in DEC]
    print(f"{p:.3f} & " + " & ".join(cells) + r" \\")

print("\n% --- matching-decoder category split (no_matching, wrong_logical) ---")
for p in sorted(by):
    for d in ('MWPM-stim', 'MWPM-chain'):
        nm, wl = split(by[p][d])
        print(f"p={p:.3f} {d}: coverage {nm}, wrong-logical {wl}")

print("\n% --- findings numbers ---")
p1 = by[0.001]
bp, relay = int(p1['BP+OSD']['failures']), int(p1['Relay-BP']['failures'])
chain = int(p1['MWPM-chain']['failures'])
print(f"p=0.001: BP+OSD {bp}/20000 ({bp/20000:.4%}), Relay-BP {relay}/20000, "
      f"MWPM-chain {chain}/20000 ({chain/20000:.4%})")
if bp and not relay:
    print(f"Relay-BP < 1.50e-4 (exact one-sided CP UB, 0/20000); "
          f"BP+OSD/Relay lower ratio bound: {bp/20000 / (2.996/20000):.1f}x")
pen = (chain / 20000) / (bp / 20000)
print(f"chain-graphification penalty at p=0.001: {pen:.1f}x")
if len(by) > 1:
    print("penalty across grid (MWPM-chain LER / BP+OSD LER): "
          + ", ".join(f"p={p:g}: "
                      f"{(int(by[p]['MWPM-chain']['failures']) / max(1, int(by[p]['BP+OSD']['failures']))):.1f}x"
                      for p in sorted(by)))
print(f"coverage failure (MWPM-stim no_matching): "
      + ", ".join(f"p={p:g}: {by[p]['MWPM-stim']['no_matching']}"
                  for p in sorted(by)))
