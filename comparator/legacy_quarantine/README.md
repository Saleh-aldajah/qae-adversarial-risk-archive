# Legacy quarantine (second-round review, finding sec. 4.7)

These files are quarantined out of the active pipeline:

- `wsc_insert.py` — latent contamination route: merged the obsolete
  wsc_a/b/c CSVs into the active `results/wsc_circuit.csv`. Superseded
  by `wsc_circuit_point.py` (per-point, checkpointed, resume-capable)
  and `gen_wsc_table.py` (deterministic table generation).
- `wsc_a.csv`, `wsc_b.csv`, `wsc_c.csv` (+ logs) — pre-C01-repair WSC
  runs on the reversed-CNOT extraction circuit. Not to be merged into
  any active result. Retained only for provenance.

Nothing in this directory is referenced by `reproduce_all.py`, the
manuscript, or any validator.

## 2026-09-25 incident (v25 preparation): `wsc_v23_reversed_rerun_20260925/`

During v25 preparation we discovered that the *working* tree (outside this
archive) still carried the v23 reversed-extraction `wsc_circuit_point.py`,
and that its `results/wsc_circuit.csv` (dated 2026-08-28) was byte-identical
to the archived v23-invalid CSV. A six-rate rerun launched from the working
tree was therefore producing reversed-circuit data (per-point CSVs and
intra-point checkpoints, all quarantined in
`wsc_v23_reversed_rerun_20260925/`).

Detection route: per-point DEM digests — the rerun's p=0.002 DEM hash
matched the v23-era file (d0509d73...) instead of the corrected circuit
(a80e06f9...). Containment: jobs halted; outputs quarantined here; the
corrected script restored from the shipped v24 archive ZIP and re-verified
(DEM-hash regression at p=0.001 reproduces a80e06f9...; `wsc_verify.py` all
four groups PASS); resume logic hardened so rows without
`circuit_rev=v24-corrected-extraction` never count as completed.

The archive's corrected record
(`../results/wsc_circuit.csv`, exp `wsc_circuit_v24`) is unaffected and is
byte-identical to the v24 submission package's copy.
