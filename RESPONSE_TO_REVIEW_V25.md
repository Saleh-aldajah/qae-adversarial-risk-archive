# QAE v25 — Response to the Second-Round Review ("Review Against Improvement Plan")

Maps the second-round review's closure matrix (C01–C11), its five release
gates (§7), and its §4 defect list to the actions taken in v25, with one
artifact per action. "Manuscript" refers to `v17-manuscript/main_v24.tex`
(44 pp build of 2026-09-25). Statuses are one of **completed**,
**completed-with-scope-note**, **withdrawn**, **partially completed
(deferred)**, or **not claimed** — no item is marked closed because its
wording changed.

Summary of the round: Gate 1 and Gate 2 are completed in full; Gate 3 is
completed for every claim the manuscript currently makes (the one incomplete
campaign is disclosed as such and supports no headline claim); Gate 4 is
completed for the offline tree, with the hardware campaigns explicitly
classed as records; Gate 5 is completed pending author-side metadata
(authors 2–5, CRediT, AI-use statement, Zenodo DOI) that only the authors
can supply.

---

## 1. Release gates (review §7)

### Gate 1 — One correct mathematical and semantic contract — COMPLETED

The specification the gate asks for now exists as the semantic contract of
§4 (protected asset, implementation, attack class, native-noise assumptions,
decoder, endpoint, coverage domain) plus the new Table `tab:riskcert`, which
prints the contract's output per system. The four named counterexample
classes are repaired at the level of theorem text, not phrasing:

| Review case | v24 defect | v25 repair |
|---|---|---|
| Weighted decoding | `thm:spacetime` proved |C|≤|F| while claiming minimum-weight matching | Hypothesis restated as **minimum-cardinality** decoding (uniform-weight MWPM); proof uses exactly that; a *Weighted decoders* paragraph shows that for a general weight functional w(·) the failure condition is 2·w(F) ≥ min_logical w(L), i.e. a radius in the decoder's own fault metric; all prior-weighted MWPM statements are labeled numerical, not deduced |
| Noisy-syndrome sufficiency | — | The proposition's scope is detector-level sufficiency; the noisy-syndrome endpoint question is exactly the C07 classifier repair (below), separated per the gate |
| Tied cosets | `prop:syndrome-insufficiency(i)` claimed "exactly one half corrected" — false for k≥2 (reviewer's [[4,2,2]] example) | Statement withdrawn and replaced: residuals r₁=[C(σ)⊕E₁], r₂=r₁+[L] are distinct cosets, hence max(q(E₁),q(E₂))=1; for k=1 the (0,1) split is exact; for k≥2 both halves may fail (the reviewer's [[4,2,2]] example is now worked into the text), and the pair (C(σ),E₁) restores a universal (0,1) separation because the decoder's own correction is benign by construction |
| Max upper bound | U_W aggregation took maxima over non-exhaustive sets | New rule (Remark `rem:intervals` + `gen_risk_certificate_v24.py`): L_W = max over **tested** sets of valid lower bounds; U_W = simultaneous upper only under exhaustive coverage, else U_W = 1 with the gap printed. One Bonferroni family over all K = 676 cells (α_cell = 7.40e-05), exact Clopper–Pearson throughout |

The title and abstract were re-checked against the strongest actual result
(the certified envelope with exact radius points), and the abstract's
protocol description now names the retrospective estimand correction.

**Acceptance-criterion status**: an independent reader can reconstruct each
theorem's scope from its statement; the four counterexample classes are
either ruled out by hypothesis or worked into the text as disclosed cases.

### Gate 2 — One traceable inference pipeline — COMPLETED

- **Category function fixed** (`run_inj_boundary_decoders_v24.py`,
  `categorize()`): classification is by the *true* residual
  r = ĉ ⊕ e_n ⊕ inj; `invalid_residual` iff syn(r) ≠ 0. Four regression
  tests (T1: planted m ≠ 0 must classify invalid; T2: nonzero true residual
  with zero observed syndrome; T3: clean correction; T4: sharp w=3 half
  pairs) run at every launch, and `IBD_TEST_ONLY=1` runs only the tests.
- **Rerun audit disclosed**: the archived-arrays audit confirms the
  reviewer's verification — **0 trials** of the flagged mislabel type (old
  valid → new invalid). The repaired classifier reclassifies **24,343**
  trials (2.24% of 1,088,000 cells) in the converse direction (old invalid →
  new valid: corrections that matched the true but not the observed
  syndrome); **0** abort↔valid transitions. Every downstream table
  (`tab:injbound`, availability numbers) was regenerated from the rerun.
- **Intervals centralized**: all zero-count bounds are exact Clopper–Pearson
  via `stats_intervals.cp_interval` (the hardware-ablation "CZ gate
  decoherence only" arm now reports < 0.000999, not the Wilson 0.00128);
  adaptive arms use Robbins uniform-mixture confidence sequences
  (`gen_rc_adaptive_cs.py` → `rc_adaptive_cs_v24.csv`); the λ ladder uses
  exact CP ratio bounds (`compute_lambda_v24.py`).
- **Chronology published**: new Appendix `app:chronology` +
  `tab:chronology` — a dated ledger (campaign, what was frozen before
  data-taking, estimand status, amendments) with the standing consequence
  that nothing beyond the listed pinnings is described as pre-registered.
  Ten "pre-registered" phrasings swept to "pinned"/"hash-pinned" with
  retrospective disclosures at each point of use.
- **Negative results preserved**: the withdrawn falsification verdict, the
  BP-guided/UF invalid-residual rates, and the U_W = 1 gaps are all printed
  as such.

### Gate 3 — Complete only the experiments the paper claims — COMPLETED (with one disclosed exception)

The headline claims in v25 rest on completed experiments only. The one
incomplete campaign — the corrected WS-C circuit grid — is confined to its
own subsection with the explicit sentence that the p = 0.001 point is
complete and verified while the remaining six rates "deposit to the archive
as they land"; it supports no headline claim. **v25 preparation incident and
containment** (detailed in §4 below): during v25 preparation we found that
the *working tree* still carried the v23 reversed-extraction script and a
stale CSV identical to the quarantined v23-invalid file; both were
quarantined, the corrected script was restored from the shipped v24 package,
verified by DEM-hash regression (sha256 a80e06f9… at p = 0.001, matching the
archived corrected record) and by all four `wsc_verify.py` test groups, and
the six-rate campaign was relaunched under the corrected, checkpointed
runner. No invalid number entered the manuscript at any point: the shipped
v24 archive's corrected CSV is byte-identical to the record the manuscript
quotes.

### Gate 4 — A clean, complete release — COMPLETED for the offline tree

- Missing software package supplied: `qec-emulator/` vendored into the
  archive (egg-info and caches stripped).
- Import paths fixed: `comparator/cmp_common.py` now puts `qae_experiments/`
  on `sys.path` (the shipped archive's `run_grid.py` ImportError is gone).
- Dependency files reconciled: `environment.yml` regenerated to match
  `requirements.txt` pin-for-pin (Python 3.12, numpy 2.5.2, scipy 1.18.1,
  stim 1.16.0, ldpc 2.4.1, pymatching 2.2.2, relay-bp 0.2.2, pandas 3.0.5,
  matplotlib 3.11.1) — the versions that produced the v24/v25 artifacts.
- Offline master extended (`reproduce_all.py`): now covers the confidence
  sequences, the risk certificate, the endpoint regression tests, and the
  claim map, in addition to the v24 suite; quick validation and full
  regeneration are separately named (`--quick` vs default; heavy arms behind
  `--skip-adaptive` / `--skip-ibd`).
- Seed validation extended to all v24 families
  (`validate_seed_consistency.py`): RCv24, E3v24, E3v24p010 (per-batch
  seeds), IBDv24 constant replay seed, REP-EXACT, and the WSC family —
  651 rows, 0 mismatches.
- Machine-readable claim-to-artifact manifest added
  (`gen_claim_map_v25.py` → `data/claim_artifact_map_v25.csv`): 18 central
  claims, each with manuscript location, artifact, generator, regeneration
  class, and an explicit scope statement; the generator refuses to emit the
  map if any referenced file is missing.
- Historical files outside the active build: `comparator/legacy_quarantine/`
  holds the reversed-extraction artifacts (including the 2026-09-25 rerun
  outputs) with a README documenting the contamination route.

Author-side remainder (cannot be done from this environment): a second
person running the master script on a clean machine, and the Docker build.

### Gate 5 — An honest submission package — COMPLETED (author-side metadata pending)

- Cover letter rewritten from the validated inventory: "audit-grade"
  removed; "pinned ex ante" replaced by the true chronology (hash-pinned
  before submission; campaign-1 conditioning estimand retrospective and
  disclosed); the risk certificate described as the machine-checkable
  artifact it now is; the regeneration sentence scoped (simulation/analysis
  artifacts regenerate; hardware outcomes are records; the WS-C grid's
  completion state is stated).
- Bibliography re-verified against the web records: arXiv 2304.11119 removed
  from the IBM Nature 2023 entry (it is the Morvan et al. RCS phase-transition
  paper); `Pacenti2026trapping` authorship corrected (Michele Pacenti, Nithin
  Raveendran, Bane Vasic); `beverland2025failfast` authorship corrected
  (Michael E. Beverland, Malcolm Carroll, Andrew W. Cross, Theodore J.
  Yoder).
- "First" claim: retained only as "To our knowledge …" in the cover letter,
  absent from the manuscript's claim inventory.
- Compiled PDF visually inspected; 0 undefined references; the one >20 pt
  overfull (the chronology table) fixed by re-sizing its columns.

Author-side remainder: authors 2–5 with CRediT roles, the AI-use statement,
Zenodo DOI minting, and the venue upload.

---

## 2. Closure matrix — second-round status

| Finding | Second-round gap (review §2) | v25 action | Status |
|---|---|---|---|
| C01 circuit validity | only one of seven rates present | corrected runner restored and verified; six-rate campaign relaunched with intra-point checkpointing; merge script enforces circuit_rev on every row; manuscript states exactly which rates are complete | **completed-with-scope-note** (single verified point at freeze; grid deposits as it lands; stale-script incident disclosed in §4) |
| C02 Pauli bridge | channel interpretation needs validated logical endpoints | the endpoint repair (C07) supplies true-residual endpoints; the sum/either-sector relation is stated with its assumptions; unrelated nominal tables no longer appear under the adversarial-risk umbrella (risk certificate separates systems) | **completed-with-scope-note** |
| C03 fixed-mask inference | "preregistered" mislabeling | chronology ledger + sweep of ten phrasings; retrospective status printed at each point of use | **completed** |
| C04 finite probing | false U_W aggregation; "sound and complete" reinstated; artifact absent | aggregation rule corrected; "sound and complete" does not appear; `risk_certificate_v24.csv` + `tab:riskcert` delivered and code-generated | **completed** |
| C05 theorem scope | under-specified costs/boundaries | scope statements per theorem; weighted-decoder caveat; cardinality hypothesis explicit | **completed-with-scope-note** (architectural comparisons remain out of scope by statement) |
| C06 native noise | model-conditioned nonviolations as blanket confirmation | calibration tails labeled model predictions; placement remains a descriptive pilot (p = 0.042, exact 0.0517, method-sensitive) | **completed-with-scope-note** |
| C07 failure endpoints | classifier unsound for noisy syndromes; coverage overclaimed | true-residual classifier + regression tests + rerun audit + availability measure; "full spacetime coverage" phrasing removed in favor of tested-domain statements | **completed** |
| C08 reproduction | master omits experiments; deps incomplete; seeds unchecked | master extended (CS, risk certificate, endpoint tests, claim map); dependency files reconciled; seed validator covers all v24 families (651 rows) | **completed** for the offline tree |
| C09 statistical claims | CS claimed but not implemented | CS implemented (`stats_intervals.cs_interval`) and applied to every adaptive arm; matching-family conclusions narrowed to tested constructions | **completed** |
| C10 novelty/references | method not demonstrated; bib errors | risk-certificate artifact demonstrates the method end-to-end on the pinned instances; three bib records corrected and web-verified | **completed-with-scope-note** (the §8 scalable-method program is explicitly future work) |
| C11 assurance semantics | evidence mis-scoped; finite probes as full coverage | claim-to-artifact map carries a scope statement per claim; endpoint table reports the tested probe domain only | **completed** |

## 3. The risk-certificate artifact (C04's missing deliverable)

`qae_experiments/gen_risk_certificate_v24.py` regenerates
`qae_experiments/data/risk_certificate_v24.csv` (11 rows) and the LaTeX rows
of `tab:riskcert`. Rules implemented: L_W = max over tested sets of valid
lower bounds; U_W = max of simultaneous uppers only under exhaustive
coverage, else 1; one Bonferroni family over all K = 676 statistical cells
(α_cell = 7.40e-05); exact Clopper–Pearson via `stats_intervals.cp_interval`.
Headline values: BB72 noiseless W=2 exact per decoder (0/0/1/1 for
BP+OSD/MW-lookup/UF/BP-guided — radius incompleteness certified for the two
graph decoders); BB72 noiseless W=3 exact L=U=1 via 830 deterministic
witnesses (40,016 sampled cells, 33.6%/sector); BB72 noisy W=2 L=0.0147 and
W=3-halves L=0.8857; REP5 (ibm_marrakesh) W=2 L=0.0587, W=3 L=0.9703; REP7
W=4 L=0.9617; REP3 W=2 L=0.9185. Every sampled row prints U_W=1 with its
gap, per the review's demand that the upper bound be shown plainly.

## 4. Incidents found and contained during v25 preparation (disclosed)

1. **WS-C stale-script contamination (caught before release).** The working
   tree's `comparator/wsc_circuit_point.py` was the v23 reversed-extraction
   version, and the working `results/wsc_circuit.csv` (dated 2026-08-28) was
   byte-identical to the quarantined v23-invalid file. A six-rate rerun
   launched from the working tree was therefore generating reversed-circuit
   data. Detection route: per-point DEM digests — the rerun's p=0.002 DEM
   hash matched the v23-era file (d0509d73…) instead of the corrected
   circuit (a80e06f9…). Containment: jobs halted; all rerun outputs and
   checkpoints quarantined under `comparator/legacy_quarantine/`; the
   corrected script restored from the **shipped** v24 archive ZIP;
   restoration proved by DEM-hash regression (a80e06f9… reproduced at
   p=0.001) and by `wsc_verify.py` (all four groups PASS); the resume logic
   was additionally hardened so rows without `circuit_rev` can never count
   as completed. The archive the reviewer holds is unaffected: its corrected
   CSV is byte-identical to the manuscript's quoted record. The campaign was
   relaunched under the corrected, checkpointed runner.
2. **Endpoint-classifier rerun shifts (expected, disclosed).** Zero archived
   mislabels of the type the reviewer flagged; 24,343 converse-direction
   reclassifications (2.24%); all dependent tables regenerated; the
   availability measure (restoration-failure with Wilson CIs) added so an
   always-aborting decoder scores 1, not 0.

## 5. Deferred, withdrawn, and not-claimed

- **Deferred (§8 program)**: the scalable certification method (verified
  decomposition / certified-relaxation upper bounds), the symmetry reduction
  preserving decoder and noise model, the mitigation-selected evaluation on
  held-out conditions. v25 delivers the exact small-instance baseline and
  the reporting format (best attack found + valid remaining upper bound +
  gap + budget + coverage) that §8 asks the central benchmark to have.
- **Deferred (author-side)**: clean-machine second-person reproduction;
  Docker build; authors 2–5 + CRediT; AI-use statement; Zenodo DOI; venue
  upload; user-side hardware rerun of `run_hw_bb72_injection.py`.
- **Withdrawn and not reinstated**: "sound and complete certification";
  "full spacetime coverage"; the v23 WSC grid; the campaign-1 falsification
  verdict; the QMAL ladder; any universal decoder-ordering claim.
- **Not claimed**: quantum authentication; post-quantum cryptography;
  security outside the stated threat model; causal placement effects.

## 6. Where to check

- Gates: `reproduce_all.py` (full suite), `validate_table_shapes.py` (46
  artifacts), `validate_seed_consistency.py` (651 rows), `verify_hashes.py`
  (archive-wide manifest).
- Risk certificate: `qae_experiments/data/risk_certificate_v24.csv` +
  `tab:riskcert`.
- Chronology: `tab:chronology` + Appendix `app:chronology`.
- Claim map: `qae_experiments/data/claim_artifact_map_v25.csv`.
- Endpoint repair: `run_inj_boundary_decoders_v24.py` (T1–T4) and
  `data/injection_boundary_decoders_v24.csv` (regenerated).
- WSC: `comparator/wsc_circuit_point.py` (circuit_rev
  `v24-corrected-extraction`), `comparator/wsc_verify.py`,
  `comparator/results/wsc_verify_report.json`,
  `comparator/merge_wsc_circuit_v25.py`,
  `comparator/legacy_quarantine/README.md`.
