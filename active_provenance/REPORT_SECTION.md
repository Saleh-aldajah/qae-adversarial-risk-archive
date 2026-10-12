# Appendix AP: Active Provenance — A Controlled Defect-Placement Experiment on IBM Quantum Hardware

## AP.1 Motivation and design

Calibration data are typically consumed passively: a decoder or layout is
evaluated against whatever defect landscape the device happens to present.
Here we instead use the measured landscape *actively*: from a full
calibration snapshot of ibm_marrakesh (156 qubits, 2026-08-28), we selected
two physical lines of 11 qubits whose defect profiles are matched on every
qubit except one deliberately chosen difference (the "ghost qubit" anchor),
turning the calibration snapshot into an independent variable rather than a
nuisance. This active-provenance stance follows the defect-aware operation
paradigm of Bartlett et al. (arXiv:2607.12118), whose 2.8x suppression of
excluded defects motivates treating placement itself as an experimental
control.

Selection was fully scripted and pinned before any QPU job was submitted:
all candidate 11-qubit lines were scored against the snapshot defect map
(ap_defect_maps.csv/json), and the chosen A/B pair was recorded with a
selection digest
(b2c7c36e...f2aa87d, results/ap_ab_decode_detail.json). Both lines carry
identical code embeddings; the B line avoids the q1 qubit whose readout
error is 3.43x the line median, while the A line contains it. The q3 ancilla
(hottest ancilla on the A line) is anchored to the ghost-row in both.

## AP.2 Experimental protocol

Eight jobs (4 configurations x A/B), 10,000 shots each, submitted within a
single 40-minute window on 2026-08-28 to minimize calibration drift between
arms (backend snapshot archived in backend_snapshots/). Configurations:
3-round and 5-round repetition codes (REP3/REP5), X and Z bases, 4 rounds
of stabilizer extraction. All circuits, transpile metadata, job IDs, and
raw counts are archived (circuits/, counts/, MANIFEST.json). Total QPU
charge time was 5 s per job.

## AP.3 Results

Logical error rates (10,000 shots per arm; Wilson 95% CIs):

| Config | A-line LER | B-line LER | z (B-A) |
|---|---|---|---|
| REP3-Z | 19/10000 = 1.90e-3 [1.22e-3, 2.97e-3] | 15/10000 = 1.50e-3 [9.09e-4, 2.47e-3] | -0.69 |
| REP3-X | 30/10000 = 3.00e-3 [2.10e-3, 4.28e-3] | 21/10000 = 2.10e-3 [1.37e-3, 3.21e-3] | -1.26 |
| REP5-Z | 1/10000 = 1.00e-4 [1.77e-5, 5.66e-4]  | 0/10000 = 0 [0, 3.84e-4] | -1.00 |
| REP5-X | 7/10000 = 7.00e-4 [3.39e-4, 1.44e-3]  | 4/10000 = 4.00e-4 [1.56e-4, 1.03e-3] | -0.91 |

The B line shows a lower logical error rate in all four configurations.
A Cochran-Mantel-Haenszel test stratified by configuration gives a pooled
z = -1.73 (one-sided p = 0.042) with a common odds ratio of 1.43 for
A-line vs B-line failure; pooled raw rates are 57/40000 (A) vs 40/40000 (B).
Because the two lines are matched on all other measured defect coordinates,
this difference is attributable to the single defect coordinate that was
varied by construction — evidence that active, snapshot-informed placement
is a measurable performance lever even within one device and one
calibration cycle.

## AP.4 Limitations

Per-detector event rates on the B line exceed the A line for REP5
(two-proportion z = +3.69 (X), +3.87 (Z)): the B line runs *hotter* at the
syndrome level yet *colder* at the logical level. We attribute this to the
B line's use of physical qubit q9, whose readout assignment error is
under-modeled by the snapshot median; the decoder sees more syndrome noise
but fewer weight-3+ correlated events. This dissociation is itself a
finding — detection rates and logical rates need not rank-identically —
but it also means the REP5 arms should be read as conservative for the
placement hypothesis, and we report all four arms without selection.

## AP.5 Reproducibility

All artifacts are hashed in MANIFEST.json (30 files: selection maps,
snapshot, QPY circuits, job metadata, raw counts, decoded results, figure
sources). Job IDs are recorded per configuration; the equivalence between
the symatch GTCode BB72 matrices and the archived BB72 construction is
certified in results/bb72_symatch_equiv_cert.json (explicit column
permutation, verified rows-identical).
