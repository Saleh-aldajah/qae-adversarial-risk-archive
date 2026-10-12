# VOICE GUIDE — three passages the authors must write themselves

Why this exists: the desk rejection flagged the prose as AI-sounding. Any text
generated for you would reproduce that problem. These briefs give you the exact
content beats and verified numbers for each passage; the sentences must be yours.
Target: 1 paragraph each, first person plural ("we"), include at least one
specific judgment or anecdote that only the people who ran the work would know.

## Passage 1 — Introduction opening (motivation)
Replace the generic opening with *why you built this benchmark*.
Content beats available:
- What broke in practice when you first ran matching decoders on BB instances
  (e.g., the 100% instantiation failure of the standard matching toolchain on
  weight-6-check circuits; DEM chain decomposition as the fallback you started from).
- The moment the DEM-decomposed MWPM numbers came back orders of magnitude worse
  than BP+OSD (risk ratios 135x at BB72 p=0.008, >1,000x at BB144/BB288).
- Why you decided the field needs a pinned, paired, provenance-logged comparison
  rather than another decoder paper.
Tone: concrete, first-person, one specific failure story. No "in recent years".

## Passage 2 — Discussion: "what surprised us"
Content beats available (all verified against CSVs):
- Bare symmetry matching failing 367/10,000 at p=0.001 while every BP-augmented
  variant failed zero — and the mechanism turning out to be structural
  (48/72 X-sector and 57/72 Z-sector weight-1 straddling faults), not calibration.
- BP+pre+simplex and BP+simplex agreeing on all 70,000 paired instances
  (predecoding fully redundant under BP) — unexpected given prior emphasis.
- On the Kunlun hardware DEM, the matching family paying 2.0-2.4x at round 1
  and the penalty decaying with depth — localization you did not expect ex ante.
- The injection campaign falsifying your own naive stochastic bound at p=0.10
  (2.1x/3.8x) while the device-aware bound held — the pre-registration doing
  exactly what it was supposed to do.
Pick the two you actually found most surprising; say why in one sentence each.

## Passage 3 — Conclusion (plain first-person-plural)
Content beats available:
- The nine scoped findings (i)-(ix) are already enumerated; the conclusion
  paragraph should say what *you* take away: e.g., that the field's baseline
  shifted in 2026, that graphification cost is measurable on hardware, and
  that pre-registered device tests of QEC theory are feasible today.
- End with what you would do next (BB spacetime-distance proof is open;
  hypergraph-native matching at circuit level; second-device replication).
Tone: short sentences, no superlatives, no "genuinely"/"substantial".

## AI-use statement
Confirm the commented template in main_v19.tex (after Conflict of interest)
against actual usage, edit, and uncomment. The editor asked for this explicitly.
