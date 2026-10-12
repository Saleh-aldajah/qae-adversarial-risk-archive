"""
wsc_circuit_point.py — WS-C: circuit-level corroboration of the graphification
penalty, complementing the Kunlun real-DEM arm with a controlled synthetic
study on our own pinned BB72 instance.

V24 REVISION (review finding C01): the v23 version of this circuit had BOTH
extraction layers' CNOT directions reversed (X-check layer used data->ancilla,
Z-check layer used ancilla->data), so the detector error model did not
represent BB72 syndrome extraction and every v23 circuit-level number was
invalid for its intended interpretation.  The corrected convention below is
verified by comparator/wsc_verify.py (deterministic, independent checks):

  * X-check (HX row, X-type stabilizer): ancilla prepared in |+>, ancilla is
    the CNOT *control*, data qubits are targets (CX anc -> d); the ancilla is
    read in the X basis (H, measure).  Z errors on data propagate onto the
    ancilla (Z_t -> Z_c Z_t) and flip the X-basis readout.
  * Z-check (HZ row, Z-type stabilizer): ancilla prepared in |0>, data qubits
    are CNOT *controls*, ancilla is the target (CX d -> anc); the ancilla is
    read in the Z basis.  X errors on data propagate onto the ancilla
    (X_c -> X_c X_t).

Design: BB72 Z-memory, r rounds of syndrome extraction under a standard
circuit-level depolarizing model (1q: p/10, 2q: p, meas flip: p, idle: p/10),
canonical serial-by-check schedule (disclosed; not an optimized schedule).
Decoders: BP+OSD (archive settings) vs chain-graphified MWPM (independent
merge) on the Stim DEM, plus Relay-BP as the SOTA reference, MWPM on the
naive Stim-decomposed graph (labeled negative control; decomposition failures
dropped), and BeliefMatch (BP-reweighted matching).
Logical observables: the 12 Z-logicals (injected basis, archive frame);
failure = any logical mispredicted.

Paired streams: Stim sampler seed = stable_seed('WSC', p, r); each decoder
sees the same shots (same DEM samples decoded by all).

Reset/preparation is ideal: R and MR resets carry no explicit
reset-preparation error channel (disclosed; the measurement-flip rate p on
MR is a readout flip, not a preparation fault).

v25 (second-round review): intra-point checkpointing every CKPT_EVERY shots
(crash-resilient resume within a point; per-point resume across points was
already v24).  Note: Relay-BP tie-breaking is not bit-deterministic across
process restarts, so a resumed point can differ from a single-pass run by
O(1) counts in the Relay-BP arm only (immaterial vs the Wilson width).
"""
import os, sys, csv, json, time, math, hashlib, argparse
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, 'qae_experiments'),
           os.path.join(ROOT, 'archive-rerun'),
           HERE):
    if os.path.isdir(_p):
        sys.path.insert(0, _p)

from bb_codes import BB72, gf2_rref, in_rowspace  # noqa: E402
from cmp_common import stable_seed, wilson95, logical_basis  # noqa: E402

CIRCUIT_REV = 'v24-corrected-extraction'


def build_circuit(rounds, p, prep_x=None, inject_x=(), inject_z=(),
                  x_prep=False, return_bookkeeping=False):
    """BB72 memory: X-ancillas measure HX rows, Z-ancillas measure HZ rows.

    Qubit ids: data 0..71, X-ancilla 72+i (i=0..35), Z-ancilla 108+j.
    Schedule per round: reset ancillas; X-check CNOTs (X-anc control -> data,
    X-basis readout); Z-check CNOTs (data control -> Z-anc); measure ancillas.
    Final: measure data (Z basis).

    Optional hooks (used by wsc_verify.py; all default to the plain memory):
      prep_x   : 0/1 vector of length 72; X gates applied to data after reset
                 (prepares a computational-basis pattern).
      inject_x : iterable of data qubits receiving an X gate after prep.
      inject_z : iterable of data qubits receiving a Z gate after prep.
      x_prep   : if True, H on all data after reset (prepare |+>^n so the
                 X-checks are deterministic; used for X-layer verification).
    """
    import stim
    HX, HZ = BB72['HX'], BB72['HZ']
    n, n2 = 72, 36
    c = stim.Circuit()

    meas_count = 0
    x_meas_pos = []   # absolute measurement positions of X anc per round
    z_meas_pos = []

    # initial data prep
    c.append('R', list(range(n)))
    if x_prep:
        c.append('H', list(range(n)))
    if prep_x is not None:
        for d in np.flatnonzero(np.asarray(prep_x, dtype=np.uint8)):
            c.append('X', int(d))
    for d in inject_x:
        c.append('X', int(d))
    for d in inject_z:
        c.append('Z', int(d))

    for r in range(rounds):
        base = meas_count
        # ---- X layer (measures HX rows; ancilla control, X-basis readout)
        for i in range(n2):
            c.append('R', 72 + i)
        for i in range(n2):
            anc = 72 + i
            c.append('H', anc)
            c.append('DEPOLARIZE1', anc, p / 10)
            for d in np.flatnonzero(HX[i]):
                c.append('CX', [anc, int(d)])
                c.append('DEPOLARIZE2', [anc, int(d)], p)
            c.append('H', anc)
            c.append('DEPOLARIZE1', anc, p / 10)
        for i in range(n2):
            c.append('MR', 72 + i, p)
            meas_count += 1
        x_meas_pos.append(list(range(base, meas_count)))
        # ---- Z layer (measures HZ rows; data control, ancilla target)
        base = meas_count
        for j in range(n2):
            c.append('R', 108 + j)
        for j in range(n2):
            anc = 108 + j
            for d in np.flatnonzero(HZ[j]):
                c.append('CX', [int(d), anc])
                c.append('DEPOLARIZE2', [int(d), anc], p)
        for j in range(n2):
            c.append('MR', 108 + j, p)
            meas_count += 1
        z_meas_pos.append(list(range(base, meas_count)))
        c.append('DEPOLARIZE1', list(range(n)), p / 10)  # data idle during meas

    # final data measurement (Z basis)
    base = meas_count
    for d in range(n):
        c.append('M', d, p)
        meas_count += 1
    final_pos = list(range(base, meas_count))

    # detectors: Z-ancilla round 0 anchored to the deterministic Z-prep
    # (valid for Z-memory prep; prep_x outside the code space fires the
    # corresponding checks, which wsc_verify.py asserts); then
    # round-to-round comparisons; final data vs last Z round.
    for j in range(n2):
        c.append('DETECTOR', [stim.target_rec(z_meas_pos[0][j] - meas_count)])
    for r in range(1, rounds):
        for j in range(n2):
            c.append('DETECTOR', [stim.target_rec(z_meas_pos[r][j] - meas_count),
                                  stim.target_rec(z_meas_pos[r - 1][j] - meas_count)])
    # X ancillas anchor nothing for Z memory; round-to-round X detectors are
    # valid because a noiseless repeated X-check measurement reproduces its
    # (random) round-0 outcome once the state is projected.
    for r in range(1, rounds):
        for i in range(n2):
            c.append('DETECTOR', [stim.target_rec(x_meas_pos[r][i] - meas_count),
                                  stim.target_rec(x_meas_pos[r - 1][i] - meas_count)])
    # final data measurement -> Z check detectors vs last Z ancilla round
    for j in range(n2):
        recs = [stim.target_rec(final_pos[d] - meas_count)
                for d in np.flatnonzero(HZ[j])]
        recs.append(stim.target_rec(z_meas_pos[-1][j] - meas_count))
        c.append('DETECTOR', recs)
    # observables: Z-logicals from injected basis
    LZ = logical_basis(BB72['HX'], BB72['HZ'], 12)
    for li, l in enumerate(LZ):
        recs = [stim.target_rec(final_pos[d] - meas_count)
                for d in np.flatnonzero(l)]
        c.append('OBSERVABLE_INCLUDE', recs, li)

    if return_bookkeeping:
        return c, dict(x_meas_pos=x_meas_pos, z_meas_pos=z_meas_pos,
                       final_pos=final_pos, meas_count=meas_count, LZ=LZ)
    return c


def build_matching_from_dem(dem, weights=None):
    """Chain-graphify a (hyper) DEM into PyMatching, tracking observables.

    Each DEM error instruction with detectors D = (d1..dk) and observable
    flips O becomes a chain of edges d1-d2, ..., d(k-1)-dk (|D|=1: boundary
    edge); every edge carries fault_ids = O so decode() returns predicted
    observable flips directly. weights overrides instruction probabilities
    (used for belief-matching posterior reweighting). Parallel edges use the
    'independent' merge strategy; a high-weight global boundary balances odd
    syndromes. This mirrors the reference BeliefMatching construction.
    """
    import pymatching
    m = pymatching.Matching()
    wmax = 1.0
    wlist = []
    for k, instr in enumerate(dem.flattened()):
        if instr.type != 'error':
            continue
        q = float(instr.args_copy()[0])
        w = weights[k] if weights is not None else max(
            0.0, math.log((1 - min(max(q, 1e-12), 1 - 1e-12)) /
                          min(max(q, 1e-12), 1 - 1e-12)))
        dets, obs = [], set()
        for t in instr.targets_copy():
            s = str(t)
            if s.startswith('D'):
                dets.append(int(s[1:]))
            elif s.startswith('L'):
                obs.add(int(s[1:]))
        wlist.append(w)
        wmax = max(wmax, w)
        if len(dets) == 0:
            continue
        if len(dets) == 1:
            m.add_boundary_edge(dets[0], weight=w, fault_ids=obs,
                                merge_strategy='independent')
        else:
            for a, b in zip(dets[:-1], dets[1:]):
                m.add_edge(a, b, weight=w, fault_ids=obs,
                           merge_strategy='independent')
    # global boundary on all detectors seen
    ndet = dem.num_detectors
    for i in range(ndet):
        m.add_boundary_edge(i, weight=100.0 * wmax, merge_strategy='independent')
    return m


def dem_instruction_weights_bp(bp, s):
    """BP posteriors per DEM instruction (bp: pre-constructed BpDecoder)."""
    from scipy.special import expit
    bp.decode(s)
    ppost = np.clip(expit(-np.asarray(bp.log_prob_ratios)), 1e-12, 1 - 1e-12)
    return list(np.maximum(0.0, np.log((1 - ppost) / ppost)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ps', nargs='+', type=float,
                    default=[0.001, 0.002, 0.004, 0.006, 0.008, 0.010, 0.012])
    ap.add_argument('--rounds', type=int, default=4)
    ap.add_argument('--shots', type=int, default=20000)
    ap.add_argument('--out', default=os.path.join(HERE, 'results', 'wsc_circuit.csv'))
    args = ap.parse_args()

    import stim
    from ldpc import BpOsdDecoder
    import scipy.sparse as sp
    import relay_bp
    import pymatching

    rows = []
    done_ps = set()
    if os.path.exists(args.out):
        with open(args.out) as _f:
            for _r in csv.DictReader(_f):
                # circuit_rev must be present AND match: rows from the v23
                # reversed extraction (no circuit_rev column) must never be
                # accepted as done (contamination guard, review finding C01).
                if (int(_r['shots']) == args.shots and
                        int(_r['rounds']) == args.rounds and
                        _r.get('circuit_rev') == CIRCUIT_REV):
                    done_ps.add(float(_r['p']))
        if done_ps:
            print('resuming; already done:', sorted(done_ps), flush=True)
    for p in args.ps:
        if p in done_ps:
            continue
        circ = build_circuit(args.rounds, p)
        dem = circ.detector_error_model(decompose_errors=False)
        # sampled arrays are seeded and identical across restarts; caching
        # them avoids re-sampling on every sandbox reboot (v25)
        samples_path = args.out + f'.p{p}.samples.npz'
        if os.path.exists(samples_path):
            _z = np.load(samples_path)
            det, obs = _z['det'], _z['obs']
            if det.shape[0] != args.shots:
                raise SystemExit(f"stale samples cache {samples_path}")
        else:
            sampler = dem.compile_sampler(
                seed=stable_seed('WSC', p, args.rounds))
            det, obs, _errs = sampler.sample(args.shots, return_errors=True)
            det = det.astype(np.uint8)
            obs = obs.astype(np.uint8)
            np.savez_compressed(samples_path, det=det, obs=obs)
        # matrices from DEM (allow hyperedges for BP decoders)
        from symatch_prep import detector_error_model_to_check_matrices
        mats = detector_error_model_to_check_matrices(dem, allow_undecomposed_hyperedges=True)
        H = mats.check_matrix          # (dets, errors) sparse
        OBS = mats.observables_matrix  # (12, errors)
        priors = np.asarray(mats.priors, dtype=np.float64)
        Hd = H.toarray().astype(np.uint8) if sp.issparse(H) else np.asarray(H, np.uint8)
        OBSd = OBS.toarray().astype(np.uint8) if sp.issparse(OBS) else np.asarray(OBS, np.uint8)

        # decoder constructions
        bposd = BpOsdDecoder(sp.csr_matrix(Hd.astype(np.float64)),
                             channel_probs=list(priors), max_iter=100,
                             bp_method='ms', ms_scaling_factor=0.625,
                             osd_method='osd_cs', osd_order=7)
        relay = relay_bp.RelayDecoderF64(sp.csr_matrix(Hd.astype(np.float64)),
                                         error_priors=priors.copy())
        # matching-family on the DEM graph
        mwpm_chain = build_matching_from_dem(dem)               # prior weights
        # Native stim hyperedge decomposition FAILS on this DEM (intrinsic
        # correlated mechanisms from weight-6 checks) — itself a reportable
        # finding; ignore_decomposition_failures drops them (naive baseline).
        dem_graph = circ.detector_error_model(decompose_errors=True,
                                              ignore_decomposition_failures=True)
        mwpm_stim = pymatching.Matching.from_detector_error_model(dem_graph)
        from ldpc import BpDecoder
        bp_for_bm = BpDecoder(sp.csr_matrix(Hd.astype(np.float64)),
                              channel_probs=list(priors), max_iter=100,
                              bp_method='ms', ms_scaling_factor=0.625)

        fails = {k: 0 for k in ['BP+OSD', 'Relay-BP', 'MWPM-chain',
                                'MWPM-stim', 'BeliefMatch']}
        nomatch = {k: 0 for k in fails}
        t0 = time.time()
        t_start = 0
        # ---- intra-point checkpoint resume (v25) ---------------------------
        ckpt_path = args.out + f'.p{p}.ckpt.json'
        if os.path.exists(ckpt_path):
            with open(ckpt_path) as _cf:
                _ck = json.load(_cf)
            if (_ck.get('shots') == args.shots and
                    _ck.get('rounds') == args.rounds and
                    _ck.get('circuit_rev') == CIRCUIT_REV and
                    _ck.get('seed') == stable_seed('WSC', p, args.rounds)):
                fails.update(_ck['fails'])
                nomatch.update(_ck['nomatch'])
                t_start = int(_ck['done_t'])
                t0 -= float(_ck.get('elapsed', 0.0))
                print(f"  WSC24 p={p:.3f}: resuming at shot {t_start}/"
                      f"{args.shots} from checkpoint", flush=True)
            else:
                print(f"  WSC24 p={p:.3f}: ignoring stale/mismatched "
                      f"checkpoint {ckpt_path}", flush=True)
        CKPT_EVERY = 500
        for t in range(t_start, args.shots):
            s = det[t]
            a = obs[t]
            for name in fails:
                try:
                    if name == 'BP+OSD':
                        cdec = np.asarray(bposd.decode(s), dtype=np.uint8)
                        pred = (OBSd @ cdec) % 2
                    elif name == 'Relay-BP':
                        cdec = np.asarray(relay.decode(s), dtype=np.uint8)
                        pred = (OBSd @ cdec) % 2
                    elif name == 'MWPM-chain':
                        pred = np.zeros(12, dtype=np.uint8)
                        pr = np.asarray(mwpm_chain.decode(s), dtype=np.uint8)
                        pred[:min(12, len(pr))] = pr[:12]
                    elif name == 'MWPM-stim':
                        pred = np.asarray(mwpm_stim.decode(s), dtype=np.uint8)
                    else:  # BeliefMatch
                        w = dem_instruction_weights_bp(bp_for_bm, s)
                        bm = build_matching_from_dem(dem, weights=w)
                        pred = np.zeros(12, dtype=np.uint8)
                        pr = np.asarray(bm.decode(s), dtype=np.uint8)
                        pred[:min(12, len(pr))] = pr[:12]
                except ValueError:
                    # no perfect matching exists -> decoder cannot answer;
                    # counted as a logical failure (disclosed)
                    nomatch[name] += 1
                    fails[name] += 1
                    continue
                if not np.array_equal(pred, a):
                    fails[name] += 1
            if (t + 1) % CKPT_EVERY == 0 and (t + 1) < args.shots:
                with open(ckpt_path, 'w') as _cf:
                    json.dump(dict(shots=args.shots, rounds=args.rounds, p=p,
                                   circuit_rev=CIRCUIT_REV,
                                   seed=stable_seed('WSC', p, args.rounds),
                                   done_t=t + 1, fails=fails, nomatch=nomatch,
                                   elapsed=time.time() - t0), _cf)
        dt = time.time() - t0
        p_rows = []
        for name, k in fails.items():
            lo, hi = wilson95(k, args.shots)
            row = dict(exp='wsc_circuit_v24', code='BB72', decoder=name,
                       rounds=args.rounds, p=p, shots=args.shots, failures=k,
                       no_matching=nomatch[name],
                       ler=round(k / args.shots, 6), ci_lo=round(lo, 6),
                       ci_hi=round(hi, 6), seed=stable_seed('WSC', p, args.rounds),
                       sec=round(dt, 2), circuit_rev=CIRCUIT_REV,
                       dem_sha256=hashlib.sha256(str(dem).encode()).hexdigest())
            p_rows.append(row)
            print(f"  WSC24 {name:11s} p={p:.3f}: {k:5d}/{args.shots} "
                  f"(nomatch {nomatch[name]}) [{lo:.5f},{hi:.5f}]", flush=True)
        # crash-resilient: append this p's rows immediately
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        exists = os.path.exists(args.out)
        with open(args.out, 'a', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(p_rows[0].keys()))
            if not exists:
                w.writeheader()
            for r in p_rows:
                w.writerow(r)
        rows.extend(p_rows)
        for _tmp in (ckpt_path, samples_path):
            if os.path.exists(_tmp):
                os.remove(_tmp)  # point complete: drop intra-point state

    print('wsc done ->', args.out)


if __name__ == '__main__':
    main()
