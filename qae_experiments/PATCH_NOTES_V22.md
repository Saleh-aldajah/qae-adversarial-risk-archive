# Patch Notes — v22 (2026-09-24)

Scope: repair of two referee-level defects and integration of the
"innovation vision" package. No new hardware data (the IBM account
currently exposes zero instances; BB-capable devices remain
inaccessible); all additions are theory, formalization, or analysis of
existing pinned data.

## Defect repairs

- `fig:ab` (active-provenance figure) is now referenced in the Appendix A
  prose alongside `tab:ab`.
- Corollary 3 (CSS spacetime correctability) decoder scope: new
  Remark "Decoder instantiation of Corollary 3" delineates exactly which
  conclusions implemented decoders inherit (radius region: yes,
  exhaustively, via the certified LookupDecoder; beyond radius: the
  corollary is silent and the manuscript's claims there are empirical —
  no pi-bound is asserted for BP+OSD).

## New formal results (derived from existing theorems + measured data)

- Proposition (Syndrome-oracle insufficiency): syndrome monitoring is a
  strictly weaker integrity certificate than logical-level injection
  probing; proof by structure (Theorem 3(a)) and exhibition (measured
  anti-correlated REP5 A/B pair: syndrome hotter z=+3.69/+3.87, logically
  colder, CMH one-sided p=0.042).
- Corollary (Soundness and completeness of injection certification):
  the pinned injection protocol is sound (Theorem 3(a)) and complete
  (Theorem 3(b)) within the spacetime fault model.
- Corollary (Adversarial work factor): minimum adversarial weight t+1;
  3/6/9 for BB72/BB144/BB288 vs 1 for the rate-matched independent-patch
  baseline; unbounded ratio for any constant-rate family with unbounded d.

## New analysis artifact

- `data/lambda_ladder.csv` + `compute_lambda.py`: distance-ladder
  suppression factor Lambda per Delta d = 2 step from the adaptive RC
  CSVs (deterministic, <1 s). Headline: Lambda = 2.63 [1.89, 3.64]
  (p=0.010) and 2.49 [1.97, 3.14] (p=0.012) over d=6->18, vs the
  surface-code benchmark 2.14 +/- 0.02 (cited, scope-disclaimed).

## Framework

- New Discussion subsection "A certification reading: quantum memory
  integrity assurance" (QMAL-1..5, QMIC certification status:
  repetition memories QMAL-5 on two devices; BB72 QMAL-3 + partial
  QMAL-4 pending BB-capable hardware). Claim map gains four rows;
  abstract carries the QMIC thesis (245 words by PDF extraction);
  conclusion gains items (x)-(xii).

Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
