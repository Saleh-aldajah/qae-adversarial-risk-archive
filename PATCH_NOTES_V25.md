# PATCH NOTES — v25 (second-round review repairs)

Date: 2026-09-25. Base: v24 (first-round reconstruction). Driver document:
`QAE_v24_Review_Against_Improvement_Plan.docx` (closure matrix C01–C11,
release gates G1–G5, §8 innovation program). The point-by-point mapping is
`RESPONSE_TO_REVIEW_V25.md`; this file lists the engineering delta.

## Manuscript (v17-manuscript/main_v24.tex, 43 → 44 pp)

- `thm:spacetime`: hypothesis restated as minimum-cardinality decoding;
  weighted-decoder caveat added (radius in the decoder's fault metric);
  prior-weighted MWPM results labeled numerical.
- `prop:syndrome-insufficiency(i)`: "exactly one half corrected" withdrawn;
  replaced by the distinct-coset statement max(q(E1),q(E2))=1 with the k=1
  exact case, the reviewer's [[4,2,2]] counterexample worked in, and the
  universal (0,1) separation via (C(σ),E1). `cor:workfactor` tie-breaking
  sentence corrected accordingly.
- New `tab:riskcert` (11 rows, K=676 Bonferroni, exact CP) after
  `rem:intervals`; U_W=1-with-gap rule printed.
- New `app:chronology` + `tab:chronology`: dated 7-row ledger of
  pinnings/retrospective estimands; standing-consequence paragraph.
- ~10 "pre-registered" phrasings swept to "pinned"/"hash-pinned" with
  retrospective disclosures (abstract, contributions, rem:naive-false,
  prop:stochastic, rem:zerofail, tab:injstoch caption, finding (iii),
  consolidation, theory_test description).
- `tab:injbound` regenerated under the repaired endpoint classifier; caption
  defines invalid share via the true residual; availability paragraph added
  (restoration_failure with Wilson CIs; always-aborting decoder scores 1).
- `tab:ablation`: CZ-only arm's zero-count UB now exact CP (<0.000999).
- §5.5 (iii): witnesses certify the upper bound d≤6; exactness obligation
  explicitly assigned to the trusted checker's MITM re-run.
- WSC subsection: C01 repair narrative retained; ideal reset/preparation
  disclosed; no extrapolation of decoder ordering from one point; the two
  pairwise-reduction routes scoped to "tested reductions".
- Chronology-table column widths fixed (20 pt overfull removed).

## Experiments / code

- `run_inj_boundary_decoders_v24.py`: `categorize()` rewritten to
  true-residual semantics (invalid iff syn(ĉ⊕e_n⊕inj) ≠ 0); regression tests
  T1–T4 executed at every launch (`IBD_TEST_ONLY=1` runs only the tests);
  restoration_failure columns added. Full rerun: 0 archived mislabels of the
  flagged type; 24,343 converse reclassifications (2.24% of 1,088,000
  cells); 0 abort↔valid transitions. Pre-rerun artifacts kept as
  `data/*.prev25`.
- `stats_intervals.py` (prior v25 window): exact CP + Robbins uniform-mixture
  confidence sequences; self-check reproduces the 93.86% Wilson coverage
  counterexample.
- `gen_rc_adaptive_cs.py` → `data/rc_adaptive_cs_v24.csv` (15 rows).
- `gen_risk_certificate_v24.py` → `data/risk_certificate_v24.csv` (11 rows)
  + LaTeX rows for `tab:riskcert`.
- `gen_claim_map_v25.py` → `data/claim_artifact_map_v25.csv` (18 claims;
  self-validating; G4 machine-readable manifest).
- `validate_seed_consistency.py`: v24 families added (RCv24; E3v24 and
  E3v24p010 per-batch seeds; IBDv24 constant replay seed; REP-EXACT; WSC) —
  651 rows, 0 mismatches.
- `validate_table_shapes.py`: rc_adaptive_cs_v24 (15), risk_certificate_v24
  (11), claim_artifact_map_v25 (18) added — 47 artifacts checked.
- `reproduce_all.py`: v25 steps added (CS intervals, risk certificate, claim
  map, endpoint regression tests); `run()` accepts env overrides.
- `environment.yml` reconciled with `requirements.txt` (identical pins).

## Comparator / WS-C

- **Incident 2026-09-25**: working tree carried the v23 reversed-extraction
  `wsc_circuit_point.py` and a stale CSV byte-identical to the archived
  v23-invalid file; a six-rate rerun was generating reversed-circuit data.
  Detected via per-point DEM digests (d0509d73… vs corrected a80e06f9…).
  Jobs halted; outputs quarantined
  (`comparator/legacy_quarantine/wsc_v23_reversed_rerun_20260925/`, mirrored
  into the archive); corrected script restored from the shipped v24 ZIP;
  DEM-hash regression + `wsc_verify.py` (4/4 PASS) green; resume hardened
  (`circuit_rev` must be present and equal; no default).
- `wsc_circuit_point.py` (corrected base): intra-point checkpointing every
  500 shots; sampled-array caching (npz) so reboots skip re-sampling; point
  completion clears both checkpoint and cache; Relay-BP restart
  non-determinism (O(1) counts) disclosed in the docstring.
- `merge_wsc_circuit_v25.py`: merges the pinned p=0.001 record with the six
  v25 per-point files into `results/wsc_circuit_v24.csv` (35-row gate;
  per-point DEM-digest agreement enforced) + provenance sidecar.
- `gen_wsc_table.py`: transcribes the merged grid when present (fallback:
  single pinned point); emits the no-matching vs wrong-logical category
  split for the matching-family decoders; refuses rows without
  `circuit_rev=v24-corrected-extraction`.
- `cmp_common.py`: archive-safe sys.path (qae_experiments importable).

## Documentation / packaging

- `RESPONSE_TO_REVIEW_V25.md` (new): gate-by-gate and C01–C11 second-round
  mapping with completed / completed-with-scope-note / withdrawn /
  deferred / not-claimed distinctions.
- `cover_letter_npjQI.tex`: de-claimed ("audit-grade" out; chronology-true
  pinning language; second-round repairs disclosed; regeneration scope
  precise; risk certificate named as the machine-checkable artifact).
- `references.bib`: IBMQuantum2024 arXiv mislink removed (2304.11119 is the
  Morvan et al. RCS paper); Pacenti/Raveendran given names corrected;
  beverland2025failfast author list corrected (Malcolm Carroll et al.).
- Quarantine READMEs document both contamination routes.
- `package_v25.sh`: v25 freeze + packaging (see script header for the WSC
  grid gate).

## Numbers that changed vs v24

- `tab:injbound` endpoint rows (classifier rerun): e.g. BP+OSD X invalid
  share 0.0204 (was Wilson-era value), UF availability RF max 0.994,
  BP-guided 0.974; see the table footnotes for per-probe ranges.
- `tab:ablation` CZ-only UB: 0.00128 (Wilson) → <0.000999 (exact CP).
- `lambda_ladder_v24.csv`: interval columns recomputed as exact CP ratio
  bounds (prior v25 window).
- All other tables unchanged from v24.
