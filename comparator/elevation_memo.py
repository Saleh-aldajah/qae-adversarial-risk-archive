#!/usr/bin/env python3
"""Elevation memo skeleton: new-results sections to be merged into the v17 manuscript.
Quantitative cells marked [[GRID]], [[KUNLUN6]], [[WSC]] are filled by elevation_fill.py
once the background runs land. All other text is final."""
import os
HERE = os.path.abspath(os.path.dirname(__file__))
txt = """# Elevation Memo — v17 Manuscript Additions (post-TQE desk rejection)

Target venues after elevation: npj Quantum Information / PRX Quantum / Quantum.
This memo lists the four new evidence blocks and exactly where they enter the
manuscript. Text below is submission-ready except [[TAGGED]] numeric cells.

## Block 1 — Active provenance on hardware (new Appendix AP, cite in §I and §VI)
Source: active_provenance/REPORT_SECTION.md (final).
Headline: snapshot-informed line selection gives lower logical error rate in
4/4 configurations on ibm_marrakesh; CMH pooled z = -1.73, one-sided
p = 0.042, common odds ratio 1.43. Includes the REP5 detection-rate
dissociation limitation (disclosed, not hidden).
Placement: new appendix; one sentence in the introduction ("we additionally
demonstrate the placement lever directly on hardware, Appendix AP"); one
sentence in the discussion linking to Bartlett et al. defect-aware operation.

## Block 2 — Pinned paired decoder comparator (replaces single-decoder §IV)
Source: comparator/results/comparator_grid.csv + comparator_mcnemar.csv,
figure cmp_f1_grid.
Seven decoders x seven depolarizing rates x 10,000 *bit-identical* error
instances per rate (paired design). Decoders: BP-OSD (archive settings),
Relay-BP, symatch {bare, simplex, pre+simplex, BP+simplex, BP+pre+simplex}.
Key cells: [[GRID]]
Headline claims (to finalize with numbers):
 - Exact symatch/archive BB72 matrix equivalence certificate (column
   permutation in bb72_symatch_equiv_cert.json) — first independent
   verification that the two constructions coincide.
 - Bare symatch fails weight-1 straddling errors (48/72 X-sector, 57/72
   Z-sector) — a genuine v/h asymmetry, corroborating arXiv:2602.22770's
   own failure tables; simplex and BP-augmented variants fix all 72.
 - Paired McNemar tests give exact two-sided p-values for every decoder
   pair at every rate — a statistical standard rarely met in qLDPC decoder
   comparisons.

## Block 3 — Circuit-level corroboration, two independent arms (new §V)
### Arm A — Kunlun hardware detector model (published DEM, Zenodo CC-BY)
Source: comparator/results/kunlun_cmp.csv, figure cmp_f2_kunlun.
Five decoders on the Wang et al. (Nat. Phys. 22, 308, 2026) 18-qubit BB72
experiment DEM, 10,000 shots per point, cycles {1,3,6}:
 - Clean ordering Relay-BP <= BP-OSD(10^4 iter) < BP-only << BeliefMatch <
   MWPM-prior at every cycle count and both sectors.
 - Graphification penalty on a real hardware DEM: matching decoders are
   ~2.6x worse than BP-OSD at cycle 1 (X: 42.7% vs 21.0%).
 - Belief-matching per-shot reweighting recovers only 0.4-1.2 pp —
   quantitatively mirroring the "defect-aware decoding gains are modest"
   conclusion of arXiv:2607.12118 on independent hardware.
 - Relay-BP matches BP-OSD accuracy at 20-40x lower wall time.
 - [[KUNLUN6]]
### Arm B — Synthetic BB72 circuit-level point (WS-C)
Source: comparator/results/wsc_*.csv (on completion).
 - [[WSC]]
 - Reportable negative result: stim's native DEM decomposition FAILS on the
   weight-6-check BB72 circuit (undecomposable correlated mechanisms); the
   standard matching toolchain therefore cannot even be instantiated
   without dropping mechanisms (99% LER vs 47% BP-OSD at p=0.004, rounds=4).

## Block 4 — 2026 landscape and positioning (rewritten §II)
Source: comparator/landscape_2026.md (inline-cited, all URLs verified).
Six decoder families table; certification-standards subsection (MILP
distance certification arXiv:2606.02418, LLM-based search); Aug-2026
literature burst documented (trapping sets of DEMs, ML BB72 decoding,
telescoping decoder, Relay-BP FPGA). Section 4 gaps G1-G4 filled with our
quantitative inserts.

## Venue calibration (Section 5 of landscape_2026.md)
npj QI: emphasizes hardware relevance + open data — Blocks 1 and 3 lead.
PRX Quantum: emphasizes mechanism and rigor — Blocks 2 and 3B lead,
paired statistics foregrounded.
Quantum (journal): certification/equivalence story (Block 2 certificate +
Block 3B negative result) is the differentiator.
"""
open(os.path.join(HERE,'ELEVATION_MEMO.md'),'w').write(txt)
print('ELEVATION_MEMO.md written:', len(txt), 'chars')
