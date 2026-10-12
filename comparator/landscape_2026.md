# State of the Art and State of the Practice: qLDPC Codes, Decoders, and Benchmarking Methodology (August 2026)

**Landscape report supporting the elevation of "Provenance-Anchored Benchmarking of Bivariate-Bicycle qLDPC Codes"**

*Scope: bivariate-bicycle (BB) qLDPC codes and their decoders; hardware demonstrations; benchmarking and provenance methodology; defect-aware operation. Every quantitative claim carries an inline source; this document deliberately ends without a bibliography section.*

---

## Executive summary

The eighteen months preceding August 2026 transformed bivariate-bicycle qLDPC codes from a theoretical construction into the most aggressively contested substrate in experimental quantum error correction. Four hardware organizations have now operated BB or BB-adjacent codes on real processors — Kunlun ([Wang et al., Nat. Phys. 22, 308](https://arxiv.org/abs/2505.09684)), IonQ's breakeven demonstration, and IBM's Loon program with an integrated real-time Relay-BP decoder — while the decoder literature has fragmented into at least six distinct families (BP+OSD, Relay-BP, symmetry matching, syndrome-flip BP, list/ensemble BP, and neural variants), each claiming superiority on subtly different problem instances. This fragmentation is precisely why **pinned, paired, provenance-anchored benchmarking** — the contribution of the present work — has become methodologically necessary rather than merely desirable: when decoders are compared on un-pinned code instances with unpaired random streams, reported rankings can be artifacts of instance choice and sampling noise rather than decoder quality.

Three findings from this landscape review directly shape the elevated manuscript. First, the benchmarking conversation has shifted from single-number logical error rates to **suppression-factor ladders** (Λ) and **real-time latency budgets**, a shift crystallized by Google's below-threshold surface-code demonstration with Λ = 2.14 ± 0.02 ([Acharya et al.](https://arxiv.org/abs/2408.13687)). Second, **defect-aware hardware operation** has its first controlled experimental demonstration — defect exclusion on a 120-qubit array yielded up to 2.8× logical-error suppression while defect-aware *decoding* gave only modest gains ([Bartlett et al., arXiv:2607.12118](https://arxiv.org/abs/2607.12118)) — positioning our active-provenance A/B result as the complementary, metrology-driven arm of that research direction. Third, the community now treats **certification and independent verification as first-class requirements**: the LLM-guided code-discovery pipeline of [Cruz-Benito et al., arXiv:2606.02418](https://arxiv.org/abs/2606.02418) subjects every candidate code to GF(2) rank computation, MILP distance certification, Tanner-graph deduplication, and multi-decoder cross-checks, having previously shown that unverified BP-OSD distance estimates can be off by large factors. Our digest-pinned matrices, meet-in-the-middle distance certificates, and bit-exact reproduction checks implement exactly this verification standard for the benchmarking (rather than code-discovery) setting.

## 1. Hardware state of the art: BB codes on real processors

### 1.1 The demonstration record

The hardware baseline for BB-code experiments is now multi-platform. The Kunlun processor — a 32-qubit superconducting device with overlapping long-range couplers — operated a distance-4 BB code [[18,4,4]] and a distance-3 punctured BB code [[18,6,3]], achieving logical error rates per logical qubit per cycle of (8.91 ± 0.17)% and (7.77 ± 0.12)% respectively, with simultaneous measurement of all nonlocal weight-6 stabilizers ([Wang et al., arXiv:2505.09684](https://arxiv.org/abs/2505.09684)). Crucially for the present work, the Kunlun team released their complete detector check matrices and per-mechanism channel probabilities under CC-BY-4.0 on Zenodo, enabling the exact third-party circuit-level decoder comparison we perform — to our knowledge the first time a BB hardware dataset has been re-analyzed with decoders beyond the authors' own BP-OSD stack.

Google's below-threshold surface-code work remains the methodological reference for the entire field: logical error suppression factor Λ = 2.14 ± 0.02 per distance-2 step, a distance-7 memory at 0.143% ± 0.003% error per cycle, beyond-break-even lifetime gain of 2.4 ± 0.3 over the best physical qubit, and real-time decoding at 63 µs average latency against a 1.1 µs cycle ([Acharya et al., arXiv:2408.13687](https://arxiv.org/abs/2408.13687)). Although a surface-code result, it defines the Λ-ladder reporting format that higher-venue reviewers now expect from any code family claiming a path to fault tolerance — including BB codes, where a distance ladder (d = 6, 12, 18 across BB72/BB144/BB288) exists but has been reported only in simulation.

IBM's roadmap places the gross code at the center of its fault-tolerant architecture: the Loon processor, designed around the long-range couplers BB codes require, entered fabrication and assembly at the end of 2025 with testing through 2026, and IBM's public materials report Relay-BP decoding the gross code in under 480 ns on that architecture. The remaining announced milestones (Kookaburra and beyond) extend the BB line through the late 2020s. This commitment means that **gross-code benchmarking methodology is now industrially load-bearing**: decoder rankings on BB72/BB144 feed directly into IBM's decoder-selection pipeline.

### 1.2 Defect-aware and metrology-informed operation

The closest prior art to our active-provenance A/B experiment is the defective-component study of [Bartlett et al., arXiv:2607.12118](https://arxiv.org/abs/2607.12118), who operated distance-5 surface codes on a 120-qubit superconducting array containing fabrication defects. Their central finding is a clean separation of interventions: **excluding** underperforming components from the code lattice reduced logical errors per round from 4.49% to 1.62% (up to 2.8× suppression, and defect exclusion resurrected measurement-based logical operations with 6.3% per-round failure suppression where none existed otherwise), while **defect-aware decoding** — keeping the defective components but informing the decoder — gave only modest gains (4.49% to 4.22% in their noise-informed belief-matching arm). Equally important methodologically is their negative control: excluding *non-defective* components yielded no improvement, establishing that the gains track the defect identification rather than the lattice perturbation.

Our active-provenance work occupies the complementary cell of this design matrix: instead of excluding defective components from a fixed layout, we keep all components but **select among candidate layouts using digest-bound metrology** (readout-verification counts and syndrome-localized defect maps anchored to specific calibration snapshots). Where Bartlett et al. demonstrate that exclusion beats decoder-side accommodation for *gross* defects, our A/B result tests whether metrology-guided *selection among nominally functional qubits* yields measurable benefit — answering the natural follow-on question their control experiment poses. The two results are mutually reinforcing: both find that component-level heterogeneity is a first-order experimental variable that defect-ignorant benchmarking leaves unexploited.

## 2. Decoder state of the art for BB codes

### 2.1 The six families

The decoder landscape for BB codes in mid-2026 comprises six families with genuinely different operating points, summarized in the table below. The proliferation matters scientifically: each family was validated on different code instances, noise models, and sampling budgets, so the published "rankings" are not mutually commensurable — the precise gap our pinned paired grid addresses.

| Family | Reference | Claimed advantage | Regime demonstrated | Real-time? |
|---|---|---|---|---|
| BP+OSD (combination-sweep) | [Panteleev–Kalachev lineage; Roffe landscape, PRR 2, 043043 (2020)](https://arxiv.org/abs/2507.00254) | De facto baseline; degeneracy-aware | Universal, all BB codes | No (Gaussian elimination) |
| Relay-BP | [Müller et al., arXiv:2506.01779](https://arxiv.org/abs/2506.01779) | "Significantly outperforming BP+OSD+CS-10" on BB codes | Circuit-level BB memory | Yes — 24 ns/iteration FPGA prototype on [[144,12,12]], <1 µs/cycle below p = 3×10⁻³ ([Johnson et al., arXiv:2510.21600](https://arxiv.org/abs/2510.21600)) |
| Symmetry matching (symatch) | [Sahay & Brown, arXiv:2602.22770](https://arxiv.org/abs/2602.22770) | Matching-speed decoding via toric equivalence; BP-augmented variant competitive with SOTA | Code-capacity & phenomenological gross/cyclic-HGP/directional codes | Potentially (matching core) |
| BP-SF (syndrome flip) | [Wang et al., arXiv:2507.00254](https://arxiv.org/abs/2507.00254) | Comparable-or-better LER than BP-OSD at ~70% latency; 55% further cut when parallelized | [[144,12,12]] gross code | Yes (fully parallel, no elimination) |
| Belief-matching / BP-partial-decoder hybrids | [Higgott et al., PRX 13, 031007](https://arxiv.org/abs/2203.04948); [Caune et al., arXiv:2306.17142](https://arxiv.org/pdf/2306.17142) | Exploits hyperedge noise structure MWPM cannot represent; surface-code threshold 0.94% vs 0.82% plain MWPM | Circuit-level surface codes; HGP single-shot | Slower than MWPM (>100× unoptimized) |
| Neural / ML decoders | [Bonilla Ataides et al., PRX Intelligence (2026)](https://link.aps.org/doi/10.1103/vjn1-mbxl); [Lee et al., arXiv:2608.15760](https://arxiv.org/abs/2608.15760) | Matches/exceeds MWPM on topological codes; BB72 trained against exact ML reference | Circuit-level BB reported | Inference-bound |

Two cross-cutting observations emerge. First, **every non-trivial BP variant now claims to match or beat BP+OSD somewhere** — Relay-BP on circuit-level BB, BP-SF on the gross code, MBBP-LD across several qLDPC families ([arXiv:2605.14170](https://arxiv.org/pdf/2605.14170)) — yet these claims rest on different OSD orders, iteration budgets, and scaling factors, so the community lacks a controlled head-to-head on an identical, digest-pinned instance with paired error streams. Our grid supplies exactly that control for the gross code, including a BP+OSD control row whose bit-exact reproduction of the archived pipeline validates the harness itself. Second, the real-time frontier has crystallized around FPGA/HPC integration: IBM's Relay-BP FPGA prototype achieves 24 ns BP iterations on [[144,12,12]] ([arXiv:2510.21600](https://arxiv.org/abs/2510.21600)), the GARI decoder reports 273 ns class latency with LER 6.7×10⁻⁹ at p = 10⁻³ for a distance-12 BB code, and the THQLink architecture demonstrates 1 µs/round real-time matching-based decoding of distance-19 surface codes over an HPC link with 2.944 µs round-trip latency ([Lao et al., arXiv:2608.03948](https://arxiv.org/abs/2608.03948)). Decoder accuracy comparisons that ignore the latency axis are increasingly considered incomplete at venue level.

### 2.2 Why BP fails and how each family responds

The theoretical understanding of BP failure modes on BB codes matured substantially in 2026. The trapping-set analysis of [Pacenti, Raveendran & Vasic, arXiv:2608.11516](https://arxiv.org/abs/2608.11516) characterizes trapping sets of detector error models directly — extending the classical finite-length BP theory to the circuit-level objects that actually matter experimentally. Relay-BP's response is algorithmic: disordered memory strengths, including provably indispensable negative values, damp the oscillations and break the symmetry traps ([arXiv:2506.01779](https://arxiv.org/abs/2506.01779)). BP-SF's response is speculative post-processing modeled on classical Chase decoding: oscillating bits identify unreliable positions whose syndrome flips generate candidate vectors ([arXiv:2507.00254](https://arxiv.org/abs/2507.00254)). The symmetry-matching family sidesteps BP entirely for its core correction, using the equivalence of BB codes to toric-code copies (the "cylinder trick"), and then — this is the finding most relevant to our comparator — **requires BP augmentation anyway** on the gross code, because bare symmetry matching fails a non-trivial fraction of errors far below half the distance ([arXiv:2602.22770](https://arxiv.org/abs/2602.22770)). Our exhaustive weight-1/weight-2 correctability measurements quantify this precisely: bare symatch corrects 48/72 single-qubit errors and 2148/2556 two-qubit errors on the gross code, while its BP-augmented and over-matched variants are radius-2 exact (2556/2556), matching our pinned meet-in-the-middle certificate.

## 3. State of the practice: benchmarking methodology

### 3.1 Verification and certification standards

A methodological sea-change is visible in the code-discovery literature: [Cruz-Benito et al., arXiv:2606.02418](https://arxiv.org/abs/2606.02418) subjected ~2×10⁵ candidate codes to a staged pipeline of GF(2) rank computation, distance estimation *and certification*, mixed-integer programming, BLISS Tanner-graph deduplication, decomposability analysis, and local-Clifford equivalence checks across five evolutionary campaigns. The explicit motivation is that decoder-guided distance estimates are unreliable — their pipeline exists because BP-OSD-based distance inference had been shown to overestimate distances by large factors on some candidates. The benchmarking corollary, which our manuscript develops, is that **the same certification discipline must attach to benchmark matrices and result streams**: SHA-256-pinned parity-check matrices, meet-in-the-middle distance certificates, context-hash seed formulas, and manifest verification convert benchmarking from a narrative claim into a checkable object. Our bit-exact reproduction of the archived BP+OSD rows (identical failure counts at identical seeds) demonstrates the practical operation of this standard.

The software ecosystem now supports this practice: PyMatching 2.4 exposes independent-parallel-edge merge strategies and fault-id tracking suitable for detector-error-model work; the `ldpc` package remains the reference BP+OSD implementation; IBM released Relay-BP as open Rust/Python bindings; and the symatch authors released their symmetry-matching code — though our audit found the public release omits a helper (`check_all_subsyms0`) required by its own L/R-predecoding path and fails to complete the cylinder trick on the gross code without the paper's small-code doubling, deficiencies we document and work around. Provenance reporting at this granularity (which release, which commit, which omitted helper) is part of the state of the practice we argue for.

### 3.2 Paired designs and statistical practice

Across the hardware literature, the reporting unit has stabilized on Wilson-score confidence intervals for binomial logical error rates and on per-config z-tests for A/B comparisons; Google's Λ fits add a regression layer on distance ladders ([arXiv:2408.13687](https://arxiv.org/abs/2408.13687)), and Bartlett et al. report per-round logical error probabilities with explicit controls ([arXiv:2607.12118](https://arxiv.org/abs/2607.12118)). What remains rare — and what our work adds — is **pairing**: decoding identical sampled error instances with every candidate decoder so that differences are measured by McNemar-type discordant-pair statistics rather than by overlapping unpaired confidence intervals. Pairing converts the comparison from "are the CIs separated?" to "which decoder wins on the instances where they disagree", a materially more powerful test at fixed sample size, and it is only possible under a pinned, seed-addressable error stream — i.e., under provenance-anchored benchmarking.

The FAIR-data direction in quantum experiment (findable, accessible, interoperable, reusable calibration and count data) reinforces the same point from the data side: the Kunlun Zenodo deposit is the exemplar that made our third-party circuit-level re-analysis possible, and the DAQEC-style benchmark datasets now appearing in the community extend the pattern. Our active-provenance design goes one step further by binding the *metrology itself* — not just the counts — into the digest chain, so that a layout decision can be traced to the specific calibration snapshot and readout-verification counts that justified it.

## 4. Positioning: the gaps this manuscript fills

*Quantitative insert for G2 landed 2026-08-28 (all 30 Kunlun rows); G1 grid numbers pending the last three simplex points.*

The landscape supports four specific novelty claims for the elevated manuscript. **(G1) No pinned, paired, multi-decoder head-to-head exists for the gross code.** Relay-BP's superiority claim over BP+OSD+CS-10 was made on circuit-noise BB memory with IBM's settings ([arXiv:2506.01779](https://arxiv.org/abs/2506.01779)); symatch benchmarked under code-capacity and phenomenological noise with its own logical-assignment conventions ([arXiv:2602.22770](https://arxiv.org/abs/2602.22770)); BP-SF reported latency-normalized results on [[144,12,12]] ([arXiv:2507.00254](https://arxiv.org/abs/2507.00254)). Our grid holds the code instance, the error stream, and the trial budget fixed across all families — with the matrices certified identical to the pinned archive under an explicit permutation. **(G2) No third-party re-analysis of a released BB hardware dataset exists.** Our five-decoder comparison on the Kunlun authors' own detector matrices and channel probabilities is, to our knowledge, the first. **(G3) Active provenance is the unoccupied cell** of the defect-aware-operation design matrix adjacent to [arXiv:2607.12118](https://arxiv.org/abs/2607.12118). **(G4) Correctability certification as a comparator** — exhaustive weight-1/2 correctability tables per decoder variant against a meet-in-the-middle radius-2 certificate — is a new, immediately checkable benchmark artifact that the certification-minded community ([arXiv:2606.02418](https://arxiv.org/abs/2606.02418)) is positioned to appreciate.

### 4.1 Evidence landed: the Kunlun circuit-level comparator (G2)

Five decoders × {1, 3, 6} QEC rounds × both sectors on the Kunlun authors' own
detector matrices and per-mechanism channel probabilities
([Zenodo deposit of Nat. Phys. 22, 308 (2026)](https://arxiv.org/abs/2505.09684)),
10,000 sampled shots per point, pinned seeds. Full table:
`comparator/results/kunlun_cmp.csv`; figure: `comparator/figures/cmp_f2_kunlun`.

| Rounds | Sector | Relay-BP | BP-OSD (10⁴ it) | BP-only | BeliefMatch | MWPM-prior |
|---|---|---|---|---|---|---|
| 1 | X | **0.2082** | 0.2103 | 0.2324 | 0.4231 | 0.4270 |
| 1 | Z | **0.2223** | 0.2248 | 0.2502 | 0.5299 | 0.5365 |
| 3 | X | **0.5489** | 0.5489 | 0.5897 | 0.7507 | 0.7653 |
| 3 | Z | **0.5123** | 0.5190 | 0.5626 | 0.7836 | 0.8155 |
| 6 | X | **0.7887** | 0.7952 | 0.8208 | 0.8921 | 0.9026 |
| 6 | Z | **0.7670** | 0.7728 | 0.8111 | 0.9109 | 0.9237 |

Three reportable conclusions. **(i) Ordering is invariant**: Relay-BP ≤ BP-OSD
< BP-only ≪ BeliefMatch < MWPM-prior at every round count and both sectors —
the matching family's deficit is a property of the graphification, not of a
particular cycle count. **(ii) The graphification penalty decays with rounds as
LER saturates**: MWPM-prior/BP-OSD ratio 2.03×/2.39× (X/Z) at 1 round,
1.39×/1.57× at 3 rounds, 1.14×/1.20× at 6 rounds — early cycles carry the
information, exactly as the consolidated review anticipated (P1-13).
**(iii) Per-shot belief reweighting is a small effect on real hardware DEMs**:
BeliefMatch improves on static-prior MWPM by only 0.4–3.2 pp, quantitatively
mirroring the "defect-aware decoding gains are modest" conclusion of
[arXiv:2607.12118](https://arxiv.org/abs/2607.12118) on an independent device
and code family. Relay-BP matches or beats BP-OSD (10⁴ iterations, CS-7) at
~35× lower wall time per point (8 s vs 288 s average).

### 4.2 Evidence landed: the pinned paired grid (G1)

Seven decoders × seven depolarizing rates × 10,000 **bit-identical** paired
error instances per rate (seed `stable_seed("COMPARE","BB72",p)`), BB72 gross
code with matrices certified identical to the pinned archive under an explicit
column permutation. Full table: `comparator/results/comparator_grid.csv`;
statistics: `comparator/results/comparator_mcnemar.csv`;
figure: `comparator/figures/cmp_f1_grid`.

Logical error rate (failures / 10,000 paired trials, either sector):

| p | BP+OSD | Relay-BP | sym-BP+simplex | sym-BP+pre+simplex | sym-simplex | sym-pre+simplex | sym-bare |
|---|---|---|---|---|---|---|---|
| 0.001 | 0 | 0 | 0 | 0 | 7 | 4 | 367 |
| 0.002 | 1 | 1 | 1 | 1 | 25 | 16 | 760 |
| 0.004 | 1 | 0 | 0 | 0 | 117 | 63 | 1630 |
| 0.006 | 8 | 6 | 6 | 6 | 298 | 199 | 2360 |
| 0.008 | 12 | 14 | 13 | 13 | 458 | 324 | 2950 |
| 0.010 | 35 | 33 | 31 | 31 | 765 | 594 | 3595 |
| 0.012 | 43 | 40 | 33 | 33 | 1062 | 836 | 4349 |

Four reportable conclusions. **(i) Bare symatch is not viable on the gross
code**: it fails 367/10000 instances even at p=0.001 (the weight-1 straddling
failure mode dominates: 48/72 X-sector and 57/72 Z-sector single faults are
uncorrectable), rising to 43.5% at p=0.012 — one to two orders of magnitude
above every augmented variant at every rate (paired McNemar z up to 65.7).
**(ii) BP augmentation closes the gap completely**: symatch-BP+simplex is
statistically indistinguishable from BP+OSD and Relay-BP at all rates
(smallest exact p = 0.099 at p=0.012, trending in symatch's favor, 10 vs 20
discordant pairs), and BP+OSD vs Relay-BP are indistinguishable everywhere
(smallest p = 0.69). **(iii) With BP guidance, predecoding is fully
redundant**: symatch-BP+pre+simplex and symatch-BP+simplex produce identical
pass/fail outcomes on all 70,000 paired instances (zero discordant pairs at
every rate), while *without* BP the predecode step is worth a significant
factor (836 vs 1062 failures at p=0.012, z = −15.0). **(iv) The symmetry
exploitation itself carries a residual cost**: sym-simplex trails the
BP-augmented variants by ~2-3× (1062 vs 33 at p=0.012, z = −32.0), so on this
code the six-symmetry decomposition's value is as a *posterior-consistent
fallback* for BP, not as a standalone decoder.

## 5. Venue calibration

**npj Quantum Information** and **PRX Quantum** both expect: hardware-anchored claims or clearly-decoupled simulation claims; statistical rigor at the level of Wilson/CIs and controlled comparisons; and methodological novelty beyond "yet another decoder curve". The elevated package targets this by construction: hardware A/B (WS-A), the field's first pinned paired decoder grid (WS-B), circuit-level corroboration on a released hardware dataset (WS-B Kunlun arm + WS-C), and this landscape analysis (WS-D). **Quantum** remains the fallback with its explicit reproducibility values. The residual risks are (i) the marginal-strength A/B p-value (p = 0.042 one-sided, CMH-pooled) — mitigated by framing as a consistent-direction feasibility result with an honest detection-rate limitation, exactly the framing [arXiv:2607.12118](https://arxiv.org/abs/2607.12118) uses for its modest decoder-side arm; and (ii) the fast-moving decoder literature (six relevant preprints in August 2026 alone, e.g. [arXiv:2608.11516](https://arxiv.org/abs/2608.11516), [arXiv:2608.15760](https://arxiv.org/abs/2608.15760)) — mitigated by positioning our contribution as the *methodology* (pinned paired comparison + certification) rather than a transient ranking.

---

*Prepared 2026-08-28 as workstream D of the TQE-rejection elevation project. Sections 4.1 (Kunlun comparator) and 4.2 (pinned paired grid) final.*
