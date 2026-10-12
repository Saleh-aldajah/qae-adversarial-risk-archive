# Running the causal hardware-ablation campaign (campaign 3)

`ca01_pin_build_submit.py` converts the manuscript's simulation-only
hardware ablations into causal claims on IBM Quantum hardware, and
`ca02_analyze.py` retrieves, decodes, and evaluates the pre-registered
tests. Both are self-contained within this archive (they import the
campaign-1/2 modules in `theory_test/` and `theory_test_consol/`).

## Why this runs on your machine, not in the analysis sandbox

Same reason as campaigns 1-2 (see `IBM_RUN_INSTRUCTIONS.md` in
`qae_experiments/`): the account is fully functional, but the analysis
sandbox's egress IP is blocked by Cloudflare on `quantum.cloud.ibm.com`
(HTTP 403 challenge on every API path; IAM auth itself succeeds, which is
how the token's validity was re-verified on 2026-10-10). Run locally or
in Colab.

## What the campaign does

| Arm | Circuits | Shots | Question | Pre-registered test |
|-----|----------|-------|----------|---------------------|
| D | REP5-Z with per-round idle delays 0/1000/2000/4000 ns on all qubits | 4 x 10,000 | Does experimenter-controlled idle time raise logical failure? | D1: one-sided z(4000 vs 0), alpha=0.01; D2: monotone ladder |
| P | REP5-Z on 8 path windows (ranks 0-3 + last-4 by pinned snapshot score) | 8 x 10,000 | Is calibration-informed placement causally effective? | P1: Spearman rho >= 0.75; P2: pooled worst-4 > best-4, alpha=0.01 |
| T | 4x re-run of the widest archived stochastic cell (rule-selected: REP5-X p=0.10, 50 variants) | 50 x 800 | Tighten the widest published interval | T1: merged Wilson width strictly smaller |

Total 160,000 shots in 3 jobs (D, P, T), comparable to campaign 1.

Power note (pinned in the predictions document): campaign A measured the
REP5-Z baseline at 7e-4; with d=5 fault-combination scaling of memory
time, the 4000 ns dose (total idle 12 us, ~2.5x memory time) predicts an
order-of-magnitude LFR increase, giving D1 >99% power at 10k shots/dose
for any relative effect >= 3x.

## Setup

Identical to campaigns 1-2:

```bash
pip install "qiskit>=2.0" "qiskit-ibm-runtime>=0.49" "qiskit-aer" \
            "pymatching>=2.2" numpy
cp /path/to/ibm_token.json ./ibm_token.json     # {"token": "..."} (never printed)
```

Run from the archive root's `theory_test_causal/` directory.

## Step 0 — offline validation (no credentials, no quota)

```bash
python ca01_pin_build_submit.py --selftest
```

Expected: `SELFTEST PASS` (8 noiseless checks: all dose and placement
circuits decode to zero; stochastic samples consistent with mask weight).
This exact selftest was run pre-release and passes.

## Step 1 — dry run (credentials, no quota)

```bash
python ca01_pin_build_submit.py --dry-run
```

Snapshots the device, applies the pinned selection rules, writes and
SHA-256-pins `predictions/predictions_causal_<ts>.json`, transpiles and
digests all 62 circuits, and stops before submission.

## Step 2 — pin + submit

```bash
python ca01_pin_build_submit.py
```

Prints the predictions digest and three job IDs (saved to
`results/causal_jobs.json`). Runtime is dominated by queueing; execution
is minutes.

## Step 3 — retrieve, decode, evaluate

```bash
python ca02_analyze.py
```

Verifies the pinned predictions digest before decoding, then writes
`results/causal_results.csv` and `results/causal_verdict.json` with the
D1/D2/P1/P2/T1 outcomes, plus per-circuit raw counts under `results/`.

## Blinding note

The scripts read the token from `./ibm_token.json` and never print it.
Predictions, selections, circuits, counts, and verdicts contain no
author-identifying material.
