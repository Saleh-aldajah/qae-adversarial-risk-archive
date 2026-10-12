#!/usr/bin/env python3
"""
run_hw_bb72_injection.py  —  QMAL-4 hardware injection probing of BB[[72,12,6]]
on IBM Quantum Heron-r2 devices (ibm_fez / ibm_kingston / ibm_marrakesh).

Purpose
-------
Hardware execution of the injection-budget game (manuscript Theorem 3 and
Corollary cor:workfactor) on the BB72 code:

  * control probes   W=0,1,2 : random X (resp. Z) patterns of weight <= t=2.
                    Theorem 3(a): ideal extraction corrects all of them.
  * sharpness probes W=3     : halves of *certified* weight-6 logical operators
                    (obligation O5, bb72_certificate_report.json).  The two
                    halves T, T' of a weight-6 logical L = T + T' have equal
                    syndrome, so a minimum-weight decoder resolves the
                    ambiguity incorrectly with probability ~1/2, i.e. the
                    logical failure rate must jump at W = t+1 = 3
                    (Theorem 3(b) sharpness).

The measured contrast  LFR(W<=2) ~ 0  vs  LFR(W=3 halves) ~ 1/2  is the
hardware signature of the injection boundary, completing QMAL-4 for BB72.

Protocol (one-sided memory, X-error side described; Z side symmetric)
---------------------------------------------------------------------
  1. prepare |0>^72 on data (a +1 eigenstate of every Z-type operator,
     hence of all Z stabilisers and all Z logicals),
  2. inject the X pattern T (one gate layer),
  3. run `rounds` rounds of Z-check syndrome extraction
     (36 weight-6 checks, one ancilla each -> 108 physical qubits),
  4. final measurement of all data qubits in the Z basis (perfect anchor),
  5. decode the detector history offline with BP+OSD (same settings as the
     manuscript's simulation campaign), correct the final data string, and
     declare a logical failure iff the residual is outside rowspan(HX).

Detectors: D_1 = meas_1 (virtual round 0 is trivially +1 by construction),
D_r = meas_{r-1} XOR meas_r, D_{R+1} = meas_R XOR (HZ @ final_bits).

Modes
-----
  --selftest   full pipeline on a local simulator (no credentials needed):
               ideal stabiliser run must give LFR=0 for W<=2 and ~1/2 for
               the certified sharpness halves; optional noise rehearsal.
  --dryrun     build + transpile the full probe matrix against the selected
               backend and print the QPU-time budget table; submits nothing.
  --smoke      submit ONE control circuit (W=0, rounds=1, 200 shots) to the
               real backend, decode it, and write outputs.  Costs seconds.
  --execute    submit the full probe matrix and write the archive CSV/JSON.

Auth: token is read from a JSON file {"token": "..."} (never printed).
Default search: --token-file, $IBM_TOKEN_FILE, ./ibm_token.json.

Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
import argparse, hashlib, json, os, sys, time
from itertools import combinations

import numpy as np


# ---------------------------------------------------------------- GF(2) utils
def gf2_rref(M):
    A = M.copy() & 1
    m, n = A.shape
    rank, pivots = 0, []
    for c in range(n):
        piv = next((r for r in range(rank, m) if A[r, c]), None)
        if piv is None:
            continue
        A[[rank, piv]] = A[[piv, rank]]
        for r in range(m):
            if r != rank and A[r, c]:
                A[r] ^= A[rank]
        pivots.append(c)
        rank += 1
    return A[:rank], pivots


def gf2_null(M):
    """Basis of the right nullspace of M (columns = free variables)."""
    A = M.copy() & 1
    m, n = A.shape
    rank, pivots = 0, []
    for c in range(n):
        piv = next((r for r in range(rank, m) if A[r, c]), None)
        if piv is None:
            continue
        A[[rank, piv]] = A[[piv, rank]]
        for r in range(m):
            if r != rank and A[r, c]:
                A[r] ^= A[rank]
        pivots.append(c)
        rank += 1
    free = [c for c in range(n) if c not in pivots]
    basis = []
    for f in free:
        v = np.zeros(n, dtype=np.uint8)
        v[f] = 1
        for i, p in enumerate(pivots):
            if A[i, f]:
                v[p] = 1
        basis.append(v)
    return np.array(basis, dtype=np.uint8)


def in_rowspace(v, rref, pivots):
    v = v.copy() & 1
    for row, col in zip(rref, pivots):
        if v[col]:
            v ^= row
    return not v.any()


def quotient_basis(H_stab, H_opp):
    """Representatives of ker(H_opp) modulo rowspan(H_stab): logical basis.

    For Z logicals: H_stab = HZ, H_opp = HX  (vectors in ker HX mod row HZ).
    """
    null = gf2_null(H_opp)
    rref, piv = gf2_rref(H_stab)
    kept_rows = list(rref)
    reps = []
    for v in null:
        if not in_rowspace(v, *gf2_rref(np.array(kept_rows, dtype=np.uint8))):
            reps.append(v)
            kept_rows.append(v)
    return np.array(reps, dtype=np.uint8)


def col_syns(H):
    m, n = H.shape
    return [int(sum((int(H[i, j]) & 1) << i for i in range(m))) for j in range(n)]


def syn_of_support(support, cols):
    s = 0
    for q in support:
        s ^= cols[q]
    return s


def stable_seed(*args):
    """Deterministic 32-bit seed (first 4 bytes of SHA-256, big-endian)."""
    key = "|".join(str(a) for a in args).encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:4], "big")


def wilson95(k, n):
    if n == 0:
        return (0.0, 0.0)
    z, ph = 1.959964, k / n
    den = 1 + z * z / n
    cen = ph + z * z / (2 * n)
    adj = z * ((ph * (1 - ph) + z * z / (4 * n)) / n) ** 0.5
    return (max(0.0, (cen - adj) / den), min(1.0, (cen + adj) / den))


# ------------------------------------------------------------- BB72 code spec
def build_bb(ell, m, a_exp, b_exp):
    Il = np.eye(ell, dtype=np.uint8)
    Im = np.eye(m, dtype=np.uint8)
    x = {i: np.kron(np.roll(Il, i, 1), Im) for i in range(ell)}
    y = {i: np.kron(Il, np.roll(Im, i, 1)) for i in range(m)}
    a0, a1, a2 = a_exp
    b0, b1, b2 = b_exp
    A = (x[a0] ^ y[a1] ^ y[a2]).astype(np.uint8)
    B = (y[b0] ^ x[b1] ^ x[b2]).astype(np.uint8)
    HX = np.hstack([A, B]).astype(np.uint8)
    HZ = np.hstack([B.T, A.T]).astype(np.uint8)
    return dict(ell=ell, m=m, n=2 * ell * m, HX=HX, HZ=HZ,
                HX_rref=gf2_rref(HX)[0], HX_pivots=gf2_rref(HX)[1],
                HZ_rref=gf2_rref(HZ)[0], HZ_pivots=gf2_rref(HZ)[1],
                hx_cols=col_syns(HX), hz_cols=col_syns(HZ))


BB72 = build_bb(6, 6, (3, 1, 2), (3, 1, 2))
N_DATA = BB72["n"]                    # 72
N_CHECKS = BB72["HX"].shape[0]        # 36 per type
LZ = quotient_basis(BB72["HZ"], BB72["HX"])   # 12 Z-logical reps (ker HX mod row HZ)
LX = quotient_basis(BB72["HX"], BB72["HZ"])   # 12 X-logical reps
assert LZ.shape[0] == 12 and LX.shape[0] == 12, "logical basis failure"

# O5-certified lex-first witnesses (bb72_certificate_report.json)
O5_LEX_Z = (0, 1, 2, 3, 20, 22)       # weight-6 Z-type logical (X-error probes)
O5_LEX_X = (0, 3, 6, 12, 27, 30)      # weight-6 X-type logical (Z-error probes)





# ------------------------------------------------------------ circuit factory
def build_probe_circuit(side, pattern, rounds):
    """One-sided BB72 memory circuit with an injected Pauli pattern.

    side='X': inject X (bit flips) on `pattern`; Z-check extraction
              (36 ancillas, |0>, data->anc CNOTs); final Z-basis readout.
    side='Z': inject Z (phase flips); X-check extraction (ancilla |+>,
              anc->data CNOTs); final X-basis readout.

    Qubits: data 0..71, ancillas 72..107.
    Cbits:  round r (0-indexed) check c -> cbit r*36+c  (r < rounds);
            data qubit q            -> cbit rounds*36+q.
    """
    from qiskit import QuantumCircuit
    H = BB72["HZ"] if side == "X" else BB72["HX"]
    ncb = rounds * N_CHECKS + N_DATA
    qc = QuantumCircuit(N_DATA + N_CHECKS, ncb)
    if side == "Z":
        qc.h(range(N_DATA))                      # |+>^72
    for q in pattern:
        (qc.x if side == "X" else qc.z)(q)       # injection layer
    qc.barrier()
    anc = lambda c: N_DATA + c
    for r in range(rounds):
        for c in range(N_CHECKS):
            support = list(np.flatnonzero(H[c]))
            if side == "X":
                for q in support:
                    qc.cx(q, anc(c))
                qc.measure(anc(c), r * N_CHECKS + c)
                qc.reset(anc(c))
            else:
                qc.h(anc(c))
                for q in support:
                    qc.cx(anc(c), q)
                qc.h(anc(c))
                qc.measure(anc(c), r * N_CHECKS + c)
                qc.reset(anc(c))
        qc.barrier()
    if side == "Z":
        qc.h(range(N_DATA))
    for q in range(N_DATA):
        qc.measure(q, rounds * N_CHECKS + q)
    return qc


# --------------------------------------------------------------- offline decode
def build_singleshot_circuit(side, pattern):
    """SPAM-limited injection probe: prep + injection + immediate readout.

    No extraction rounds and no two-qubit gates: the Z (resp. X) stabiliser
    syndrome is computed classically from the final data readout, which for
    the product preparation is an exact syndrome measurement up to SPAM
    noise.  This isolates the decoder/certificate layer (Theorem 3 boundary)
    from fault-tolerant extraction, which on heavy-hex requires a
    co-designed embedding (naive routing: ~2,400 CZ per round -- measured
    2026-09-24 with FakeKingston; see IBM_RUN_INSTRUCTIONS.md).

    Qubits: data 0..71.  Cbits: data qubit q -> cbit q.
    """
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(N_DATA, N_DATA)
    if side == "Z":
        qc.h(range(N_DATA))
    for q in pattern:
        (qc.x if side == "X" else qc.z)(q)
    if side == "Z":
        qc.h(range(N_DATA))
    for q in range(N_DATA):
        qc.measure(q, q)
    return qc


def make_singleshot_decoder(side, p_eff):
    from ldpc import BpOsdDecoder
    H = BB72["HZ"] if side == "X" else BB72["HX"]
    return BpOsdDecoder(H, error_rate=p_eff,
                        channel_probs=np.full(H.shape[1], p_eff),
                        bp_method="ms", ms_scaling_factor=0.625,
                        osd_method="osd_cs", osd_order=7, max_iter=100)


def decode_singleshot(side, dec, bits):
    """bits: 72 data outcomes.  Syndrome = H @ bits (perfect for product
    prep up to SPAM); residual = bits XOR correction; failure iff residual
    is a nontrivial logical."""
    data = bits[:N_DATA].astype(np.uint8)
    syn = ((BB72["HZ"] if side == "X" else BB72["HX"]) @ data) & 1
    corr = dec.decode(syn).astype(np.uint8)[:N_DATA]
    residual = (data ^ corr) & 1
    if side == "X":
        benign = in_rowspace(residual, BB72["HX_rref"], BB72["HX_pivots"])
        lbits = (LZ @ residual) & 1
    else:
        benign = in_rowspace(residual, BB72["HZ_rref"], BB72["HZ_pivots"])
        lbits = (LX @ residual) & 1
    return int(not benign), "".join(map(str, lbits.tolist()))


def spacetime_matrix(H_single, rounds):
    """E3-consistent phenom spacetime matrix for `rounds` extraction rounds
    plus one perfect anchor round (final data readout).  Returns
    He of shape ((rounds+1)*36, (rounds+1)*72 + (rounds+1)*36)."""
    R = rounds + 1
    Ir = np.eye(R, dtype=np.uint8)
    Hm = np.zeros((R * N_CHECKS, R * N_CHECKS), dtype=np.uint8)
    for r in range(R):
        for c in range(N_CHECKS):
            Hm[r * N_CHECKS + c, r * N_CHECKS + c] = 1
            if r + 1 < R:
                Hm[(r + 1) * N_CHECKS + c, r * N_CHECKS + c] = 1
    return np.hstack([np.kron(Ir, H_single), Hm])


def make_decoder(side, rounds, p_eff):
    from ldpc import BpOsdDecoder
    H_single = BB72["HZ"] if side == "X" else BB72["HX"]
    He = spacetime_matrix(H_single, rounds)
    cp = np.full(He.shape[1], p_eff)
    return BpOsdDecoder(He, error_rate=p_eff, channel_probs=cp,
                        bp_method="ms", ms_scaling_factor=0.625,
                        osd_method="osd_cs", osd_order=7, max_iter=100)


def decode_shot(side, rounds, dec, bits):
    """bits: np.uint8 array of length rounds*36+72 (cbit order).
    Returns (fail, logical_bits) — fail=1 iff corrected residual is a
    nontrivial logical; logical_bits = 12 per-logical action bits."""
    meas = [bits[r * N_CHECKS:(r + 1) * N_CHECKS] for r in range(rounds)]
    data = bits[rounds * N_CHECKS:rounds * N_CHECKS + N_DATA]
    H_single = BB72["HZ"] if side == "X" else BB72["HX"]
    anchor = (H_single @ data) & 1                       # perfect final round
    dets = np.zeros((rounds + 1) * N_CHECKS, dtype=np.uint8)
    prev = np.zeros(N_CHECKS, dtype=np.uint8)            # virtual round 0
    for r in range(rounds):
        dets[r * N_CHECKS:(r + 1) * N_CHECKS] = meas[r] ^ prev
        prev = meas[r]
    dets[rounds * N_CHECKS:] = anchor ^ prev
    raw = dec.decode(dets)
    corr = np.zeros(N_DATA, dtype=np.uint8)
    for r in range(rounds + 1):
        corr ^= raw[r * N_DATA:(r + 1) * N_DATA].astype(np.uint8)
    residual = (data.astype(np.uint8) ^ corr) & 1
    if side == "X":
        benign = in_rowspace(residual, BB72["HX_rref"], BB72["HX_pivots"])
        lbits = (LZ @ residual) & 1
    else:
        benign = in_rowspace(residual, BB72["HZ_rref"], BB72["HZ_pivots"])
        lbits = (LX @ residual) & 1
    return int(not benign), "".join(map(str, lbits.tolist()))


def counts_to_bitarrays(counts, ncb, shots):
    """qiskit counts {'01..': k} -> list of np arrays in cbit order."""
    out = []
    for s, k in counts.items():
        s = s.replace(" ", "")
        arr = np.array([int(ch) for ch in s[::-1]], dtype=np.uint8)
        assert len(arr) == ncb, f"bitstring length {len(arr)} != {ncb}"
        out.extend([arr] * k)
    return out


# ---------------------------------------------------------------- probe matrix
def probe_matrix(n_probe_logicals, seed_tag):
    """Deterministic probe list per side.  Each entry:
    dict(side, kind, weight, pattern, partner, logical_id, seed)."""
    probes = []
    for side in ("X", "Z"):
        cols = BB72["hz_cols"] if side == "X" else BB72["hx_cols"]
        witness = O5_LEX_X if side == "X" else O5_LEX_Z
        stab = ("HX" if side == "X" else "HZ")
        rref, piv = (BB72["HX_rref"], BB72["HX_pivots"]) if side == "X" \
                    else (BB72["HZ_rref"], BB72["HZ_pivots"])
        pairs = certified_halves(witness, cols, rref, piv, n_probe_logicals)
        rng = np.random.default_rng(stable_seed(seed_tag, side, "patterns"))
        probes.append(dict(side=side, kind="control", weight=0, pattern=(),
                           partner=None, logical_id=None,
                           seed=stable_seed(seed_tag, side, "w0")))
        for i in range(3):                            # W=1 random singles
            q = int(rng.integers(N_DATA))
            probes.append(dict(side=side, kind="random1", weight=1,
                               pattern=(q,), partner=None, logical_id=None,
                               seed=stable_seed(seed_tag, side, "w1", i)))
        for i in range(4):                            # W=2 random pairs
            ab = tuple(sorted(rng.choice(N_DATA, 2, replace=False).tolist()))
            probes.append(dict(side=side, kind="random2", weight=2,
                               pattern=ab, partner=None, logical_id=None,
                               seed=stable_seed(seed_tag, side, "w2", i)))
        for li, (T, Tp) in enumerate(pairs):          # W=3 certified halves
            for tag, pat in (("a", T), ("b", Tp)):
                probes.append(dict(side=side, kind="sharp3", weight=3,
                                   pattern=pat, partner=tag, logical_id=li,
                                   seed=stable_seed(seed_tag, side, "w3", li, tag)))
    return probes


# extend certified_halves with explicit stabiliser arguments
def certified_halves(witness, cols, stab_rref, stab_pivots, n_probe_logicals=4):
    """Split certified weight-6 logicals into equal-syndrome halves T, T'.

    `cols` is the syndrome column set of the *detecting* checks, and
    (stab_rref, stab_pivots) span the stabiliser group of the same Pauli
    type as the injected errors:  for X-error probes use hz_cols and
    rowspan(HX);  for Z-error probes use hx_cols and rowspan(HZ).
    The lexicographically first witness is the O5-certified one; further
    probe logicals come from the same MITM enumeration as
    verify_certificate.py (obligation O5).
    """
    w = sorted(witness)
    T, Tp = tuple(w[:3]), tuple(w[3:])
    assert syn_of_support(T, cols) == syn_of_support(Tp, cols)
    assert syn_of_support(w, cols) == 0
    probes = [(T, Tp)]
    if n_probe_logicals > 1:
        groups = {}
        for tri in combinations(range(N_DATA), 3):
            groups.setdefault(syn_of_support(tri, cols), []).append(tri)
        seen = {frozenset(w)}
        for s in sorted(groups, key=lambda x: (x == 0, x)):
            if len(probes) >= n_probe_logicals:
                break
            tris = groups[s]
            if s == 0 or len(tris) < 2:
                continue
            for a, b in combinations(tris, 2):
                if set(a) & set(b):
                    continue
                L = frozenset(a) | frozenset(b)
                if len(L) != 6 or L in seen:
                    continue
                vec = np.zeros(N_DATA, dtype=np.uint8)
                vec[list(L)] = 1
                if not in_rowspace(vec, stab_rref, stab_pivots):
                    probes.append((a, b))
                    seen.add(L)
                    break
    return probes


# -------------------------------------------------------------- backend access
BACKEND_CANDIDATES = ["ibm_fez", "ibm_kingston", "ibm_marrakesh"]


def load_token(path=None):
    cand = [p for p in [path, os.environ.get("IBM_TOKEN_FILE"), "./ibm_token.json"]
            if p]
    for p in cand:
        if os.path.exists(p):
            with open(p) as f:
                tok = json.load(f)["token"]
            print(f"[auth] token loaded from {p} (value never displayed)")
            return tok
    sys.exit("[auth] no token file found; pass --token-file or set IBM_TOKEN_FILE")


def get_service(token):
    from qiskit_ibm_runtime import QiskitRuntimeService
    return QiskitRuntimeService(channel="ibm_quantum_platform", token=token,
                                instance="open-instance")


def pick_backend(service, name):
    if name == "auto":
        cands = []
        for bn in BACKEND_CANDIDATES:
            try:
                b = service.backend(bn)
                if b.status().operational:
                    cands.append(b)
            except Exception:
                pass
        if not cands:
            sys.exit("[backend] none of %s operational" % BACKEND_CANDIDATES)
        b = min(cands, key=lambda x: x.status().pending_jobs)
        print(f"[backend] auto-selected {b.name} "
              f"(pending={b.status().pending_jobs})")
        return b
    return service.backend(name)


# ------------------------------------------------------------- transpile/budget
def transpile_probe(qc, backend, seed, opt_level, cherry_pick=False):
    from qiskit import transpile
    kw = {}
    if cherry_pick:
        try:
            ro = []
            props = backend.properties()
            for q in range(backend.num_qubits):
                try:
                    ro.append(props.readout_error(q))
                except Exception:
                    ro.append(1.0)
            kw["initial_layout"] = np.argsort(ro)[:qc.num_qubits].tolist()
        except Exception as e:
            print(f"[layout] readout cherry-pick unavailable: {e}")
    return transpile(qc, backend=backend, optimization_level=opt_level,
                     seed_transpiler=seed, scheduling_method="alap", **kw)


def budget_table(tprobes, shots):
    """tprobes: list of (probe, transpiled_circuit).  Returns total seconds."""
    rows, total = [], 0.0
    for pr, tqc in tprobes:
        dur_us = None
        try:
            dur = tqc.estimate_duration()        # needs scheduling + target
            dur_us = float(dur) * 1e6 if dur is not None else None
        except Exception:
            pass
        if dur_us is None:                       # heuristic fallback
            dur_us = 3 * tqc.depth() * 0.07 + 4.0
        est_s = shots * dur_us * 1e-6 + 3.0      # +3s per-job overhead
        total += est_s
        rows.append((pr["side"], pr["kind"], pr["weight"], tqc.depth(),
                     tqc.size(), round(dur_us, 1), round(est_s, 1)))
    return rows, total


# -------------------------------------------------------------------- selftest
def run_selftest(rounds, shots, n_probe_logicals, noisy, p_eff, extraction):
    """Full pipeline on the local stabiliser simulator."""
    from qiskit_aer import AerSimulator
    if noisy:
        from qiskit_ibm_runtime.fake_provider import FakeKingston
        from qiskit_aer.noise import NoiseModel
        nm = NoiseModel.from_backend(FakeKingston(), thermal_relaxation=False)
        sim = AerSimulator(method="stabilizer", noise_model=nm)
        print("[selftest] NOISY stabiliser rehearsal (FakeKingston noise, "
              "thermal relaxation off)")
    else:
        sim = AerSimulator(method="stabilizer")
        print("[selftest] ideal stabiliser run")
    print(f"[selftest] extraction={extraction}")
    probes = probe_matrix(n_probe_logicals, "SELFTEST")
    if extraction == "singleshot":
        decs = {s: make_singleshot_decoder(s, p_eff) for s in ("X", "Z")}
        ncb = N_DATA
        build = lambda pr: build_singleshot_circuit(pr["side"], pr["pattern"])
        decode = lambda pr, bits: decode_singleshot(pr["side"],
                                                    decs[pr["side"]], bits)
    else:
        decs = {s: make_decoder(s, rounds, p_eff) for s in ("X", "Z")}
        ncb = rounds * N_CHECKS + N_DATA
        build = lambda pr: build_probe_circuit(pr["side"], pr["pattern"],
                                               rounds)
        decode = lambda pr, bits: decode_shot(pr["side"], rounds,
                                              decs[pr["side"]], bits)
    pair_out = {}
    n_fail_ctrl = 0
    n_ctrl = 0
    for pr in probes:
        qc = build(pr)
        res = sim.run(qc, shots=shots,
                      seed_simulator=pr["seed"]).result()
        counts = res.get_counts()
        fails = 0
        for bits in counts_to_bitarrays(counts, ncb, shots):
            f, _ = decode(pr, bits)
            fails += f
        pr["fails"] = fails
        if pr["kind"] == "sharp3":
            pair_out.setdefault((pr["side"], pr["logical_id"]), []).append(fails)
        else:
            n_fail_ctrl += fails
            n_ctrl += shots
        print(f"  {pr['side']}-side {pr['kind']:8s} w={pr['weight']} "
              f"pat={pr['pattern']}: {fails}/{shots}")
    ok = True
    if not noisy:
        # Theorem 3(a): all W<=2 probes must succeed on ideal extraction
        if n_fail_ctrl != 0:
            print(f"SELFTEST FAIL: control probes {n_fail_ctrl}/{n_ctrl} "
                  "(expected 0)")
            ok = False
        # Theorem 3(b): for every certified pair (T, T'), the halves carry
        # identical detector data, hence one decoder output C; the residuals
        # T+C and T'+C differ by the nontrivial logical L, so AT LEAST one
        # half must fail every shot (the adversary injects the failing half;
        # both may fail if BP+OSD resolves to a third minimum-weight rep).
        for key, fl in pair_out.items():
            if max(fl) != shots:
                print(f"SELFTEST FAIL: pair {key} -> {fl} "
                      f"(expected max == {shots})")
                ok = False
    print("SELFTEST " + ("PASS" if ok else "FAIL"))
    return ok


# ------------------------------------------------------------------ execution
def bits_from_pub_result(pub_result, ncb, shots):
    data = pub_result.data
    creg = getattr(data, "c", None)
    if creg is None:
        creg = list(data.values())[0]
    try:
        strings = creg.get_bitstrings()
    except AttributeError:
        counts = creg.get_counts()
        return counts_to_bitarrays(counts, ncb, shots)
    out = []
    for s in strings:
        s = s.replace(" ", "")
        out.append(np.array([int(ch) for ch in s[::-1]], dtype=np.uint8))
    return out


def execute_probes(service, backend, probes, rounds, shots, opt_level,
                   p_eff, out_prefix, extraction="singleshot", dryrun=False):
    from qiskit_ibm_runtime import Sampler
    if extraction == "singleshot":
        decs = {s: make_singleshot_decoder(s, p_eff) for s in ("X", "Z")}
        ncb = N_DATA
        build = lambda pr: build_singleshot_circuit(pr["side"], pr["pattern"])
        decode = lambda pr, bits: decode_singleshot(pr["side"],
                                                    decs[pr["side"]], bits)
    else:
        decs = {s: make_decoder(s, rounds, p_eff) for s in ("X", "Z")}
        ncb = rounds * N_CHECKS + N_DATA
        build = lambda pr: build_probe_circuit(pr["side"], pr["pattern"],
                                               rounds)
        decode = lambda pr, bits: decode_shot(pr["side"], rounds,
                                              decs[pr["side"]], bits)
    rows, sidecar = [], {"backend": backend.name, "extraction": extraction,
                         "rounds": rounds, "shots": shots, "p_eff": p_eff,
                         "probes": []}
    built = []
    for pr in probes:
        qc = build(pr)
        tseed = stable_seed("HWBB72", "transpile", backend.name,
                            pr["side"], pr["kind"], pr["weight"],
                            pr["pattern"], rounds, extraction)
        tqc = transpile_probe(qc, backend, tseed, opt_level,
                              cherry_pick=(extraction == "singleshot"))
        built.append((pr, tqc))
    brows, total_s = budget_table(built, shots)
    print(f"{'side':4s} {'kind':8s} {'w':>1s} {'depth':>6s} {'size':>6s} "
          f"{'us/shot':>8s} {'est s':>7s}")
    for r in brows:
        print(f"{r[0]:4s} {r[1]:8s} {r[2]:>1d} {r[3]:>6d} {r[4]:>6d} "
              f"{r[5]:>8.1f} {r[6]:>7.1f}")
    print(f"TOTAL estimated QPU time: {total_s:.0f} s "
          f"({total_s/60:.1f} min; open-plan cycle budget 600 s)")
    if extraction == "rounds":
        worst_cz = max(tqc.count_ops().get("cz", tqc.count_ops().get("cx", 0))
                       for _, tqc in built)
        faults = worst_cz * p_eff
        print(f"[guardrail] worst routed two-qubit count = {worst_cz} "
              f"-> expected gate faults per shot ~= {faults:.1f}")
        if faults > 1.0:
            print("[guardrail] WARNING: routing noise exceeds the weight-3 "
                  "signal; a co-designed heavy-hex embedding is required "
                  "before rounds-mode data are interpretable.  Prefer "
                  "--extraction singleshot.")
    if dryrun:
        return
    if total_s > 540:
        print("[warn] estimate exceeds 90% of the open-plan cycle budget; "
              "reduce --shots/--rounds/--n-probe-logicals or split across "
              "cycles (CSV resume is supported).")
    csv_path = f"data/{out_prefix}.csv"
    done = set()
    if os.path.exists(csv_path):
        import csv as _csv
        with open(csv_path) as f:
            for row in _csv.DictReader(f):
                done.add((row["side"], row["kind"], int(row["weight"]),
                          row["pattern"]))
        print(f"[resume] {len(done)} probes already present in {csv_path}")
    import csv
    new = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="") as fh:
        wr = None
        for pr, tqc in built:
            key = (pr["side"], pr["kind"], pr["weight"],
                   " ".join(map(str, pr["pattern"])))
            if key in done:
                continue
            t0 = time.time()
            sampler = Sampler(mode=backend)
            job = sampler.run([tqc], shots=shots)
            print(f"[job] {job.job_id()}  {pr['side']}-{pr['kind']}"
                  f"-w{pr['weight']} {pr['pattern']} ...", flush=True)
            pub = job.result()[0]
            fails, lb_hist = 0, {}
            for bits in bits_from_pub_result(pub, ncb, shots):
                f, lb = decode(pr, bits)
                fails += f
                lb_hist[lb] = lb_hist.get(lb, 0) + 1
            lo, hi = wilson95(fails, shots)
            row = dict(date=time.strftime("%Y-%m-%d"), backend=backend.name,
                       extraction=extraction,
                       side=pr["side"], kind=pr["kind"], weight=pr["weight"],
                       pattern=" ".join(map(str, pr["pattern"])),
                       partner=pr["partner"] or "", logical_id=pr["logical_id"],
                       rounds=rounds, shots=shots, failures=fails,
                       lfr=round(fails / shots, 6),
                       ci_lo=round(lo, 6), ci_hi=round(hi, 6),
                       job_id=job.job_id(), seed=pr["seed"],
                       transpile_seed=tseed, depth=tqc.depth(),
                       runtime_s=round(time.time() - t0, 1))
            if wr is None:
                wr = csv.DictWriter(fh, fieldnames=list(row.keys()))
                if new:
                    wr.writeheader()
            wr.writerow(row); fh.flush()
            sidecar["probes"].append({**{k: (list(v) if isinstance(v, tuple)
                                            else v) for k, v in pr.items()},
                                      "failures": fails,
                                      "logical_bits_histogram": lb_hist})
            print(f"      -> {fails}/{shots} fails "
                  f"[{lo:.2e},{hi:.2e}]  ({row['runtime_s']}s)")
    with open(f"data/{out_prefix}_sidecar.json", "w") as f:
        json.dump(sidecar, f, indent=1)
    print(f"[done] rows appended to {csv_path}")


# ------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["selftest", "dryrun", "smoke", "execute"],
                    required=True)
    ap.add_argument("--extraction", choices=["singleshot", "rounds"],
                    default="singleshot",
                    help="singleshot: SPAM-limited injection probing (no 2q "
                         "gates; default, fits open-plan budget).  rounds: "
                         "full syndrome-extraction memory (requires a "
                         "co-designed heavy-hex embedding; see guardrail).")
    ap.add_argument("--backend", default="auto",
                    help="ibm_fez | ibm_kingston | ibm_marrakesh | auto")
    ap.add_argument("--token-file", default=None)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--shots", type=int, default=1000)
    ap.add_argument("--p-eff", type=float, default=0.003,
                    help="prior for BP+OSD (Heron-r2 median 2q ~3e-3)")
    ap.add_argument("--opt-level", type=int, default=3)
    ap.add_argument("--n-probe-logicals", type=int, default=4)
    ap.add_argument("--noisy", action="store_true",
                    help="selftest with FakeKingston noise rehearsal")
    args = ap.parse_args()

    if args.mode == "selftest":
        ok = run_selftest(args.rounds, args.shots, args.n_probe_logicals,
                          args.noisy, args.p_eff, args.extraction)
        sys.exit(0 if ok else 1)

    token = load_token(args.token_file)
    service = get_service(token)
    backend = pick_backend(service, args.backend)

    if args.mode == "dryrun":
        probes = probe_matrix(args.n_probe_logicals, "HWBB72")
        execute_probes(service, backend, probes, args.rounds, args.shots,
                       args.opt_level, args.p_eff, "hw_bb72_injection",
                       extraction=args.extraction, dryrun=True)
    elif args.mode == "smoke":
        probes = [dict(side="X", kind="control", weight=0, pattern=(),
                       partner=None, logical_id=None,
                       seed=stable_seed("HWBB72", "smoke"))]
        execute_probes(service, backend, probes, 1, 200, args.opt_level,
                       args.p_eff, "hw_bb72_smoke", extraction="singleshot")
    else:
        probes = probe_matrix(args.n_probe_logicals, "HWBB72")
        execute_probes(service, backend, probes, args.rounds, args.shots,
                       args.opt_level, args.p_eff, "hw_bb72_injection",
                       extraction=args.extraction)


if __name__ == "__main__":
    main()
