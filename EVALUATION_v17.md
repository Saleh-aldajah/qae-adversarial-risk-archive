# Independent evaluation of the v17 elevated package
**Scope:** `v17-manuscript/main_v17.tex` (22 pp, compiles clean), comparator + WS-C + active-provenance workstreams, archive (206 files).
**Stance:** friendly but adversarial referee at npj Quantum Information / PRX Quantum. Date: 2026-08-29.

---

## 0. Verdict

The empirical package is now strong: seven evidence layers, paired statistics, two hardware arms, and a certification-first protocol that most of the 2026 qLDPC-decoder literature does not match. **The weak point is no longer the benchmarks — it is the theory layer (§5, "ACE framework").** The theorems are standard results restated; the one quantitative prediction (the i.i.d. lower bound) has never been tested on any device; and the central conceptual object — the ACE value — has no operational, measurable definition. The paper is titled *adversarial* yet contains no adversarial experiment. This is the highest-leverage fix, and it is executable: the theory can be formalized into an *injection-budget game* with a provable spacetime bound, and that bound can be tested on IBM hardware with a pre-registered fault-injection campaign.

Overall referee-risk profile **before** this fix: moderate at npj QI ("theory is a wrapper"), high at PRX Quantum ("what is the new theorem?"). **After** the fix: the paper gains the one thing neither venue can get from the 2026 decoder literature — a *pre-registered, device-tested* adversarial guarantee.

---

## 1. Per-block assessment

### 1.1 ACE theory (§5) — **weakest block; referee target #1**
| Item | Assessment | Risk |
|---|---|---|
| Thm 1 (minimax via Sion) | Correct, acknowledged standard, but contributes no operational quantity. Existence of a saddle point is never used downstream. | M |
| Thm 2 (fidelity floor via KL + FvdG) | Correct direction, but ε_FT is the diamond-norm error of the *entire implemented recovery* — unmeasurable at scale and never bounded in the paper. Operationally vacuous as stated. | **H** |
| Prop (i.i.d. stochastic LB) | The **only quantitative prediction in the theory layer** — and it is pure arithmetic (tab:minimax), never validated against any experiment or device. | **H** |
| Remark (decoder-dependent ACE gap) | Honestly flagged "not a theorem," but it rests on LFR as a proxy for diamond norm — a proxy the text itself disavows (Limitation 7). A referee will quote this back. | **H** |
| Lemma (weight scaling) | Elementary counting; the surface-patch comparison at R=1/6 is apples-to-oranges (independent patches vs. one block). Flagged "elementary" already; keep but de-emphasize. | M |
| Adversary classes 𝔄₁/𝔄₂/𝔄₃ | 𝔄₁ has theorems; 𝔄₂ is "experiments" (not a definition); 𝔄₃ is named and dismissed. No threat model: injection points, timing, basis knowledge, win condition, security notion are all undefined. | **H** |

### 1.2 Paired grid (§6) — strong
Bit-identical instances + exact McNemar + certificate is genuinely ahead of the field. Residual risks: single code instance (BB72 only), code-capacity noise only — both already disclosed in Limitations. The finding "BP-augmented symatch ≡ BP+OSD ≡ Relay-BP, bare symatch non-viable" is clean and quotable. Risk: L.

### 1.3 Kunlun re-analysis (§8 Arm A) — strong, unique
First third-party re-analysis of a released BB hardware DEM. The round-decay of the graphification penalty (2.0–2.4× → 1.1–1.2×) and the belief-matching corroboration of arXiv:2607.12118 are real contributions. Risk: L. (One nit: Relay-BP timing comparison should state same-machine conditions — check wording.)

### 1.4 WS-C circuit-level (§8 Arm B) — strong; headline candidate
The circuit-level localization of Relay-BP's advantage (2.81× at p=0.001 despite the code-capacity tie) is the best *novel* empirical result in v17. The MWPM-stim 100% coverage failure is a quotable toolchain finding. Risk: L–M (single synthetic circuit, one mapper — disclosed).

### 1.5 Active provenance (App. A) — good, honestly scoped
p = 0.042 one-sided with disclosed REP5 dissociation is defensible *because* it is pre-pinned. It does not, however, connect to the theory layer at all — it tests placement, not any ACE statement. Risk: M (single device/cycle — disclosed).

### 1.6 Emulator + certificate + landscape — solid infrastructure
Risk: L. The certificate (d ≥ 6, t = 2 exhaustive) is underused: it is *exactly* the object needed to support a t-bounded adversarial guarantee for BB72 — currently the paper never makes that connection.

---

## 2. The core formal gap (what "formalize the theory" must mean)

1. **No operational definition of the ACE value.** Fix: define the *injection-budget game* — the adversary chooses a fault set of spacetime weight ≤ W, placed adversarially in space and time; the ACE value is the worst-case logical failure probability of the implemented memory under this game. This is measurable on a device.
2. **No provable bound under 𝔄₂.** Fix: spacetime-budget correctability theorem for distance-d repetition memories (proof by the matching-graph chain argument), plus the BB72 statement supported by the existing exhaustive t = 2 certificate.
3. **Unmeasurable ε_FT.** Fix: rigorous bridge for Pauli-approximate logical channels — for a Pauli channel, diamond distance from identity = 2(1 − p_I); hence worst-case-basis LFR bounds the logical diamond error up to a quantified twirling residual. This upgrades Remark 5.1 from "proxy" to "bound with stated approximation."
4. **No empirical test of the i.i.d. bound.** Fix: stochastic-injection arms on hardware (§3 below), plus a retroactive bound-check on the existing REP3/REP5 A/B counts (zero new QPU time).
5. **No threat model / security notion.** Fix: formal threat-model subsection — adversary controls (injection location, timing, weight budget, basis), not (syndrome decoding, calibration); security notion = bounded logical failure (integrity/availability of the memory); tamper-witness corollary: the observed detection-rate/logical-rate dissociation implies syndrome-level monitoring alone cannot certify security — logical-level monitoring is necessary. This converts a *disclosed limitation* into a *security finding*.

## 3. The empirical fix — pre-registered IBM fault-injection campaign (feasible: YES)

Backend: ibm_marrakesh (156-qubit Heron; access pattern already proven this project — QiskitRuntimeService + SamplerV2, 10k-shot arms completed 2026-08-28).

**REP5 (d = 5, t = 2) and REP3 (d = 3, t = 1) memory, both sectors, R = d rounds:**

| Arm | Injection | Theory prediction |
|---|---|---|
| base | none | LFR = δ̂ (baseline) |
| w_t worst-case | weight t, worst placement, mid-memory | **correctable** → LFR ≈ δ̂ (bound holds) |
| w_{t+1} worst-case | weight t+1, worst placement | **uncorrectable** → LFR ≈ 1 (bound sharp) |
| stochastic p ∈ {0.01, 0.02} | i.i.d. per-data-qubit, pinned seeds, 50 precompiled pattern variants × 200 shots | LFR ≤ 1 − (1 − δ̂)·Pr[Bin(d, p) ≤ t] + Wilson tolerance |

All predictions pinned (SHA-256, UTC timestamp) **before** submission — same active-provenance discipline as Appendix A. Estimated load: ~160k shots in 2–4 Sampler jobs; comparable to the completed A/B campaign.

**What this buys:** the first *device-verified* adversarial weight bound in the qLDPC/QEC-benchmark literature known to us; a direct hardware test of the paper's only quantitative theorem; and a security section with one operational definition + one tested guarantee + one monitoring corollary.

## 4. Secondary improvements (ranked, post-fix)

1. Upgrade Remark (decoder ACE gap) via the Pauli-channel diamond bridge (cheap, formal).
2. Wire the BB72 t = 2 certificate into the injection theorem as "certificate-backed correctability" (cheap).
3. Reframe the REP5 dissociation as the tamper-monitoring corollary (cheap).
4. Optional: correlated-injection arm (burst faults on a heavy-hex edge) to probe 𝔄₂ beyond i.i.d. — future work if queue time allows.
5. Keep Lemma (weight scaling) but downgrade to a remark; do not let it carry weight in the abstract.

## 5. Do-ability verdict

**Yes — fully doable with existing access and infrastructure.** Formalization: pure theory, this session. Hardware: token present, runtime pattern proven, circuit builder already supports line layouts and both sectors; injection = gate insertion at a chosen round boundary. Risks: queue latency (mitigate: submit as few jobs, poll), stochastic-arm pattern count bounded by pub limits (mitigate: 50 variants), and the usual single-device caveat (disclose; the claim is *device-level bound verification*, not universality).

---

## CLOSURE UPDATE (2026-08-29)

Every weakness identified in this evaluation is now closed in v18 (27 pp):

1. **Theory layer** — the injection-budget game is formalized (Defs 1–3, spacetime-budget correctability Thm + sharpness, diamond-bridge Prop, device-aware composed Cor), §4.1.
2. **Empirical support for the theory** — pre-registered IBM Quantum campaign on ibm_marrakesh (312 circuits, 4 jobs, 2026-08-28): distance cliff sharp (92.4–96.0% collapse at weight t+1); composed bound held on all 14 tests; naive independence-form bound falsified at p=0.10 (2.1×/3.8×) and corrected in the manuscript. Appendix B.
3. **ε_FT measurability** — decoder-gap statement upgraded from LFR proxy to a Pauli-approximation bound via ½‖Λ−id‖⋄ = 1−p_I; twirling residual disclosed in Limitations.
4. **Reset vs idle attribution (P1-11)** — closed by Monte-Carlo (reset_sensitivity/): reset material, monotone, and logically distinct from readout.
5. **Non-monotone disclosures (P1-12)** — both rows disclosed; no adaptive stopping anywhere.
6. **Claim hygiene** — 25-row claim-to-evidence map with strength column; conclusion enumerates nine scoped findings; superlatives removed.
7. **Verification** — automated audit: 217/217 manuscript table numbers match source CSVs; references clean (49 entries, all cited keys present); 27-page compile with 0 errors / 0 undefined refs / 0 overfull boxes.

Remaining items are author-identity/credential actions only — see SUBMISSION_README.md.
