# Pre-registered device test of the injection-budget bound — campaign report

**Backend:** ibm_marrakesh (156-qubit Heron r2) · **Date:** 2026-08-28 (snapshot `ibm_marrakesh_snapshot_20260828T200922Z_theorytest.json`) · **Shots:** 180,000 (312 arms) · **Predictions pinned pre-submission:** `predictions/predictions_20260828T200859Z.json`, sha256 `759169c2024d54423fd1a5eb54d46b6501fd5d9f2cd4e1e49b18978c74653cd5`.

| Job | ID | Contents |
|---|---|---|
| det_x | da8um21qtnsc73d0v3ug | 6 pubs × 10,000 |
| det_z | da8um2ce74ec73aj4n3g | 6 pubs × 10,000 |
| stoch_x | da8um31qtnsc73d0v400 | 150 pubs × 200 |
| stoch_z | da8um3ke74ec73aj4n50 | 150 pubs × 200 |

Design: REP5 (d=5, t=2) and REP3 (d=3, t=1) memories, both sectors, R=4 rounds, injection at round 2, fixed B-line layouts (injection is the only varying factor). Z-sector injects physical X gates; X-sector injects virtual Z (zero-duration frame updates — the injected fault adds no implementation noise). Noiseless end-to-end validation (Aer, same pipeline): 22/22 arms PASS before QPU submission (`tt00_simulate.py`).

## Results — deterministic worst-case arms

| arm | sector | failures/10k | LER | composed bound (Thm c, calibration π) | verdict |
|---|---|---|---|---|---|
| REP5 base | Z | 0 | 0.00000 | 0.012 | holds |
| REP5 base | X | 2 | 0.00020 | 0.012 | holds |
| REP5 w=2 (worst) | Z | 414 | 0.0414 | 0.375 | **holds** |
| REP5 w=2 (worst) | X | 506 | 0.0506 | 0.375 | **holds** |
| REP5 w=3 (worst) | Z | 9590 | 0.9590 | — | **sharp** |
| REP5 w=3 (worst) | X | 9598 | 0.9598 | — | **sharp** |
| REP3 base | Z | 14 | 0.0014 | 0.027 | holds |
| REP3 base | X | 28 | 0.0028 | 0.027 | holds |
| REP3 w=1 (worst) | Z | 276 | 0.0276 | 0.221 | **holds** |
| REP3 w=1 (worst) | X | 318 | 0.0318 | 0.221 | **holds** |
| REP3 w=2 (worst) | Z | 9292 | 0.9292 | — | **sharp** |
| REP3 w=2 (worst) | X | 9240 | 0.9240 | — | **sharp** |

## Results — stochastic arms (REP5; 50 pinned variants × 200 shots per cell)

| p | sector | failures/10k | LER | naive bound (δ₀+Bin tail+tol) | composed bound (Cor. stoch) | naive | composed |
|---|---|---|---|---|---|---|---|
| 0.01 | Z | 1 | 0.0001 | 0.0020 | 0.016 | holds | holds |
| 0.01 | X | 2 | 0.0002 | 0.0020 | 0.016 | holds | holds |
| 0.05 | Z | 6 | 0.0006 | 0.0031 | 0.035 | holds | holds |
| 0.05 | X | 9 | 0.0009 | 0.0031 | 0.035 | holds | holds |
| 0.10 | Z | 211 | 0.0211 | 0.0101 | 0.070 | **VIOLATED** | holds |
| 0.10 | X | 388 | 0.0388 | 0.0101 | 0.070 | **VIOLATED** | holds |

## Findings

1. **The distance cliff is real and sharp on hardware.** Weight-t worst-case adversarial injections remain within the composed correctability bound (both distances, both sectors); weight-(t+1) injections collapse the memory at 92.4–96.0% logical failure. The ~4–7% shortfall from 100% is native-noise rescue (order π(1)), consistent with the calibration fault model.
2. **Injection amplifies native noise as the chain argument predicts.** REP5 w=2 arms sit 100–250× above baseline (0.041/0.051 vs 0.0000/0.0002) yet an order of magnitude inside the composed bound — the first quantitative measurement of adversary–noise composition on a QEC memory.
3. **The naive independence-form stochastic bound is falsified on device** at p=0.10 (2.1×/3.8× over), while the device-aware composed bound holds on all six stochastic arms and all eight bounded deterministic arms. Hardware data selects the corrected theory.

## Reproduce

`tt00_simulate.py` (noiseless validation) → `tt01_submit.py` (pin+submit) → `tt02_analyze.py` (decode+score). Raw counts per arm in `counts/`, full arm rows in `results/theorytest_results.csv`, machine verdicts in `results/theorytest_verdict.json`, circuit digests in `circuits/circuits_metadata_theorytest.json`.

**Limitations:** single device, single calibration cycle, repetition memories only; π(k) calibration-estimated (λ_N=0.47 REP5 / 0.25 REP3), not fitted to results; stochastic variants cluster shots within 50 pinned patterns per cell.
