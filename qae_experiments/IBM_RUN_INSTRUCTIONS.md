# Running the BB72 hardware injection campaign (Extension 1)

`run_hw_bb72_injection.py` executes the injection-budget game of Theorem 3
on IBM Quantum Heron-r2 devices and completes obligation QMAL-4 for BB72
on hardware.  It is self-contained (needs only `qiskit`,
`qiskit-ibm-runtime`, `qiskit-aer`, `numpy`, `ldpc`).

## Why this runs on your machine, not in the build sandbox

Diagnosis on 2026-09-24: your account and key are fully functional
(one `open-instance`, us-east, 10 min/cycle, QPUs ibm_fez / ibm_kingston /
ibm_marrakesh allocated).  The build sandbox's egress IP is blocked by
Cloudflare on `quantum.cloud.ibm.com` (HTTP 403 on every path, for plain
HTTP clients and a real Chromium alike; IAM and Global Search hosts are
reachable, which is how the account state was verified).  Independent
confirmation that the account works from a normal network: the dashboard
shows the three allocated QPUs, and third-party runs from Google Colab
list the same devices.  => Run the script locally or in Colab.

## Setup

```bash
pip install "qiskit>=2.0" "qiskit-ibm-runtime>=0.49" "qiskit-aer" "ldpc>=2.4" numpy
cp /path/to/ibm_token.json ./ibm_token.json     # {"token": "..."}  (never printed)
```

## Step 0 — local validation (no credentials, no quota)

```bash
python run_hw_bb72_injection.py --mode selftest --extraction singleshot --shots 400
python run_hw_bb72_injection.py --mode selftest --extraction singleshot --shots 1000 --noisy
```

Expected: `SELFTEST PASS`.  Ideal run: all W<=2 probes 0 fails; every
certified sharpness pair has a systematically failing half.  Noisy
rehearsal (FakeKingston SPAM): pre-registered contrast —
W=0 ~1.3-1.6%, W=1 ~3.5-4.8%, W=2 ~4.7-13.0%, W=3 halves ~41-90%
(every pair max >= 61.5%).

## Step 1 — budget check against the live device (no quota used)

```bash
python run_hw_bb72_injection.py --mode dryrun --backend auto --shots 4000
```

Prints per-circuit routed depth/size and the total QPU-time estimate.
Singleshot circuits have no two-qubit gates (depth ~3), so the full
32-circuit matrix at 4,000 shots fits comfortably in one 10-minute
open-plan cycle.

## Step 2 — smoke test (a few seconds of QPU time)

```bash
python run_hw_bb72_injection.py --mode smoke --backend auto
```

Submits one W=0 control circuit (200 shots), decodes it, and writes
`data/hw_bb72_smoke.csv` + sidecar JSON.  Verify the job appears in your
dashboard and the row shows ~0 failures.

## Step 3 — full campaign

```bash
python run_hw_bb72_injection.py --mode execute --backend auto --shots 4000
```

Writes `data/hw_bb72_injection.csv` + `data/hw_bb72_injection_sidecar.json`.
Resume-safe: re-running skips probes already present in the CSV, so the
campaign can be split across open-plan cycles.  All probe patterns,
transpiler seeds, and layouts are deterministic
(`stable_seed('HWBB72', ...)`); job IDs are recorded per row.

## Analysis handoff

Upload `data/hw_bb72_injection*.csv/json` back to the project; the
manuscript integration (Table + Figure + QMAL-4 completion) is done from
those files.  Acceptance criteria, pre-registered 2026-09-24:

1. every W<=2 probe: LFR consistent with the SPAM-only model
   (point estimate below ~15% at p_eff = 3e-3),
2. every certified pair: max(LFR_T, LFR_T') >= 40%,
3. contrast ratio min(sharp3)/max(W<=2) >= 3.

## About `--extraction rounds`

Rounds mode implements the full one-sided syndrome-extraction memory
(108 qubits, r rounds + perfect anchor, spacetime BP+OSD identical to the
manuscript's E3 model; offline-validated: `--mode selftest
--extraction rounds` PASSes ideal and noisy).  On hardware it is gated by
routing: naive transpile onto the 156-qubit heavy-hex map yields
~2,400-2,800 CZ per extraction round (measured 2026-09-24, FakeKingston,
12 seeds, opt levels 2-3) i.e. ~7 expected gate faults per shot at
p_eff = 3e-3, which would swamp the weight-3 signal.  The script prints a
guardrail warning in this case.  A co-designed ancilla-tree embedding
(Bravyi-style, 144 of 156 qubits) is the known fix and is tracked as a
separate work package; do not run rounds mode on hardware until the
embedding lands.
