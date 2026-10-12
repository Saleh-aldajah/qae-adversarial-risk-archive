# QAE v24 — Submission checklist (author side)

All version labels are canonical v24: the manuscript zip contains
`main_v24.tex/.bbl/.pdf` and uploads directly to Overleaf as a project zip.
The manuscript compiles standalone (40 pp, 0 errors, 0 undefined references,
max overfull 4.06 pt). The abstract is 250 words — at the 250-word limit.

v24 is a full scientific reconstruction under the v23 Scientific Review and
Improvement Plan; v23 artifacts are preserved as the reviewed record
(invalid files renamed `*_INVALID`, not deleted). Headline changes:

- **Repositioning**: certified adversarial risk bounds λ_M(W) with
  simultaneous [L_W,U_W] intervals (Bonferroni joint ≥95%, exact
  Clopper–Pearson 2.996/N at zero counts, honest U_W=1 where untested);
  minimax/Knill–Laflamme explicitly background; new title and abstract.
- **C01 (critical)**: WS-C circuit extraction convention corrected;
  protocol-invariance tests T1–T4 ALL PASS (`comparator/wsc_verify.py`);
  v23 CSV renamed INVALID; corrected grid regenerated with
  `circuit_rev=v24-corrected-extraction`.
- **C03 (critical)**: the "naive bound falsified" verdict used the wrong
  estimand; mask-conditioned reanalysis (`stoch_reanalysis_v24`) reproduces
  the reviewer thresholds exactly, no cell exceeds → falsification
  **withdrawn**; composed model relabelled discovery.
- **RC v24**: aligned-priors rerun (`model_rev=v24-aligned-priors`), fixed
  grid extended to p=0.001–0.012, adaptive ladder with p=0.010 rung
  (BB72 64/4,000; BB144 2/20,000; BB288 0/20,000); Λ redefined as
  cube-root-per-block with exact-CP one-sided ratio bounds
  (`lambda_ladder_v24.csv`, 15 rows); BB144→BB288 rung reported
  unresolvable.
- **IBD v24**: exhaustive noiseless w≤2 wrong-logical per sector + noisy
  W≤2 controls + McNemar pairing (`injection_boundary_*_v24.csv`,
  `inj_radius_noiseless_v24.csv`); invalid-residual shares corrected to the
  control-set definition.
- **§5.5**: verification architecture — sectorwise sufficiency, independent
  334-line trusted checker (ALL FIVE OBLIGATIONS PASS), published witness
  schema, syndrome-consistency assertions.
- **C11**: QMAL ladder removed; scoped integrity-evidence profile with
  explicit threat model; QEC≠authentication cited; marrakesh-only provenance
  disclosed.
- **C08**: `reproduce_all.py` v24 master (offline; hardware never invoked),
  validators extended (16 new CSVs + sibling gates), dependency lock
  (stim 1.16.0, ldpc 2.4.1, pymatching 2.2.2, relay-bp 0.2.2, numpy 2.5.2),
  archive-wide manifest (1,600 files), vendored `ibm_demo_common.py`.
- **Statistics**: exact CP zero-failure bounds throughout; comparator
  risk ratio ">134,000×" at joint ≥95% (97.5%/97.5% Bonferroni).
- Documents: `PATCH_NOTES_V24.md`, `RESPONSE_TO_REVIEW_V24.md` in the
  archive root.

---

## Historical record: v23 checklist

v23 adds two calibrated experiments that close stated limitations:
the cross-decoder injection-boundary calibration (Remark rem:crossdec —
decoder radius-completeness shown to be security-relevant; BP+OSD
preserves the certified boundary at >=13x contrast, UF/BP-guided MWPM
collapse it to 1.0x) and the exact REP3 twirling-residual calibration
(Remark rem:twirl-num — LFR twirl-exact, cubic coherent residual,
bridge ratio ~2/(3 theta)). Artifacts: run_inj_boundary_decoders.py +
data/injection_boundary_decoders.csv (126 rows), run_twirling_residual.py
+ data/twirling_residual.csv (8 rows). The Extension-1 hardware runner
(qae_experiments/run_hw_bb72_injection.py) is offline-validated and
awaits author-side execution (see IBM_RUN_INSTRUCTIONS.md).

v21 closes the four Tier-1 items of the external "honest assessment"
review, all with pinned seeds and SHA-256 provenance:

v23 adds two calibrated experiments that close stated limitations:
the cross-decoder injection-boundary calibration (Remark rem:crossdec —
decoder radius-completeness shown to be security-relevant; BP+OSD
preserves the certified boundary at >=13x contrast, UF/BP-guided MWPM
collapse it to 1.0x) and the exact REP3 twirling-residual calibration
(Remark rem:twirl-num — LFR twirl-exact, cubic coherent residual,
bridge ratio ~2/(3 theta)). Artifacts: run_inj_boundary_decoders.py +
data/injection_boundary_decoders.csv (126 rows), run_twirling_residual.py
+ data/twirling_residual.csv (8 rows). The Extension-1 hardware runner
(qae_experiments/run_hw_bb72_injection.py) is offline-validated and
awaits author-side execution (see IBM_RUN_INSTRUCTIONS.md).

v21 closes the four Tier-1 items of the external "honest assessment"
review, all with pinned seeds and SHA-256 provenance:

- **E1 rare-event campaign** — 10⁶ trials per point (6 rows,
  BB72/BB144/BB288 × p ∈ {0.002, 0.004}). Full re-run on 2026-09-23
  reproduced the archived CSV byte-for-byte (sha256 `7c49da83…`).
  Risk ratios at p = 0.004 are now finite for all three codes:
  BB72 371.9× [312.7, 442.3]; BB144 17,500× [9,678, 31,643];
  BB288 > 183,000× one-sided. New Table 5 (tab:e1); bridge remark now
  ε_FT ≤ 3.2e-4 point / ≤ 3.74e-4 at 95%.
- **E3 adaptive RC extension at p = 0.010** — same pinned-seed protocol
  (`stable_seed('E3', code, p, rounds, batch)`): BB72 65/4,000;
  BB144 4/20,000 (adaptive tail 3, 4, 14 at p = 0.008/0.010/0.012 —
  monotone; the fixed-grid non-monotone pair is resolved at 10× the
  trials without dropping data); BB288 1/20,000 (tail 0, 0, 0, 1, 2 —
  monotone). New Table 9 (tab:rc_adaptive). The archived BB144 p = 0.012
  row was independently re-run and reproduced exactly (14/20,000).
- **O5: BB72 distance is d = 6 exactly** — exhaustive weight-6 kernel
  enumeration (MITM 3+3 over all C(72,3) = 59,640 triples per sector):
  120 kernel candidates and 84 + 84 nontrivial weight-6 logicals,
  2,592 anticommuting pairs, witnesses (0,1,2,3,20,22) / (0,3,6,12,27,30).
  `verify_certificate.py` now checks five obligations and regenerates
  `data/bb72_certificate_report.json` deterministically; the "d ≥ 6 not
  exact" limitation is removed.
- **Archive completeness** — `qae_experiments/data/` now ships the full
  E0–E6 evidence set (the v20 zip carried the runners but only 8 CSVs),
  plus `legacy/`, `minimax_lower_bounds.csv`, and the v16 infrastructure
  (Dockerfile, Makefile, reproduce_all.py, environment.yml). Manifest
  regenerated: 69 tracked files; `verify_hashes.py`,
  `validate_table_shapes.py`, `validate_seed_consistency.py` (223 rows),
  and `verify_certificate.py` all pass inside the archive. See
  `qae_experiments/PATCH_NOTES_V21.md`.


v22 repairs two referee-level defects and integrates the innovation
package (no new hardware data; theory + analysis of pinned data):

- **fig:ab cross-reference fixed** (Appendix A prose now cites Figure
  fig:ab alongside tab:ab).
- **Corollary 3 decoder scope repaired** — new Remark "Decoder
  instantiation of Corollary 3": radius conclusions are inherited by the
  certified LookupDecoder; beyond-radius claims are empirical; no
  pi-bound is asserted for BP+OSD.
- **Three new formal results** — Proposition (syndrome-oracle
  insufficiency; measured REP5 A/B inversion), Corollary (injection
  soundness/completeness), Corollary (adversarial work factor 3/6/9 vs
  1, unbounded ratio).
- **Distance-ladder Lambda** — 2.63 [1.89, 3.64] (p=0.010) and 2.49
  [1.97, 3.14] (p=0.012) over d=6→18 vs surface-code 2.14±0.02;
  artifact `data/lambda_ladder.csv` + `compute_lambda.py`.
- **QMIC framework** — Discussion subsection "A certification reading":
  QMAL-1..5 levels mapped to artifacts; repetition memories certified
  QMAL-5, BB72 QMAL-3 + partial QMAL-4 (live BB72 injection: runner
  shipped and offline-validated — see qae_experiments/
  IBM_RUN_INSTRUCTIONS.md.  IBM account verified working 2026-09-24
  (open plan, 10 min/cycle, ibm_fez/kingston/marrakesh allocated);
  the build sandbox itself is Cloudflare-blocked from
  quantum.cloud.ibm.com, so the hardware leg runs locally/Colab).

## 1. Author voice (the desk-rejection fix — do this FIRST)
- [ ] Write the three voice passages per `VOICE_GUIDE.md` (intro motivation,
      "what surprised us" in the Discussion, conclusion). These must be in your
      own words; AI-drafted replacements would reproduce the original flag.

## 2. Five-author block
- [ ] Replace `[AUTHOR 2: name]` ... `[AUTHOR 5: name]$^{5}$` and the four
      `$^{2..5}$[AUTHOR n: affiliation, email]` lines in `main_v23.tex`
      (title page). Corresponding-author marking: add it to the chosen author.
- [ ] Complete the Author contributions section (`[AUTHOR 2--5: ...]` slot;
      CRediT taxonomy recommended).
- [ ] Update the cover letter signature/address block (`[AUTHORS]` slots in
      `cover_letter_npjQI.tex`).

## 3. AI-use disclosure (editor explicitly asked)
- [ ] Find the commented "Use of generative AI" block after Conflict of interest
      in `main_v23.tex`, confirm it matches actual usage, edit, and uncomment.

## 4. External persistent identifiers
- [ ] Mint/verify the Zenodo DOI `10.5281/zenodo.20588043` actually resolves
      (the manuscript treats it as inactive until the public record resolves).
- [ ] Confirm the public code release link (emulator README still notes the
      repository link is inserted after public release).

## 5. Venue account actions
- [ ] Create the submission in the npj Quantum Information (or chosen venue) system.
- [ ] Upload `QAE_v22_manuscript_FINAL.zip` as the source package; confirm the
      system-built PDF matches `main_v22.pdf` (30 pp).
- [ ] Upload `QAE_v22_archive_FINAL.zip` as supplementary material / linked dataset.
- [ ] Paste the abstract (≤250 words as shipped); enter suggested reviewers.
- [ ] Confirm the Nature Quantum Computing option is NOT selected.

## 6. Final self-check (2 minutes)
- [ ] Skim pages 1 (five-author block + abstract), 8 (CSS corollary),
      9 (instantiated diamond bound, 10⁶-trial numbers), 11 (Table 5
      rare-event), 15 (Table 9 adaptive RC), 20 (O5 d = 6 certificate),
      21–27 (injection test + consolidation replication) of `main_v22.pdf`.
- [ ] Confirm IBM Quantum job IDs in Appendix B match your dashboard:
      2026-08-28 campaign: da8um21qtnsc73d0v3ug, da8um2ce74ec73aj4n3g,
      da8um31qtnsc73d0v400, da8um3ke74ec73aj4n50;
      2026-09-06 consolidation: daelek5nj4cs73afaqpg, daelekd1ierc738mai50,
      daelel642tqs73auss4g, daeleljdd5gc73d8pcrg, daelelt1ierc738mai7g,
      daelembdd5gc73d8pct0.

## Package integrity
- See `SHA256SUMS_v22.txt` (both zips + the manuscript PDF inside the zip).
