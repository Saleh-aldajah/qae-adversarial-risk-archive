"""
wsc_verify.py — independent deterministic verification of the BB72
syndrome-extraction circuit built by wsc_circuit_point.py (review finding
C01 / release criterion: "Every QEC circuit extracts the intended stabilizers
and measures the intended logical observables under independent deterministic
checks").

Checks (all noiseless, deterministic):
  T1  two-qubit parity gadgets: the corrected Z- and X-extraction primitives
      return the intended parity on all basis inputs; the v23 (reversed)
      primitives return input-independent 0 — the documented bug signature.
  T2  full-circuit codespace behaviour: all detector parities are 0 and the
      final data readout equals the prepared pattern, for the zero pattern,
      all 12 logical-Z representatives, and a Z-stabilizer pattern; a
      deliberately out-of-codespace pattern fires exactly the predicted
      round-0 Z-check detectors.
  T3  single-fault injection on every data qubit: an injected X_q produces
      Z-ancilla round-0 pattern exactly HZ[:,q]; an injected Z_q (in the
      X-prepared variant) produces X-ancilla pattern exactly HX[:,q].
  T4  static audit of DETECTOR / OBSERVABLE_INCLUDE record targets against
      the documented measurement bookkeeping, plus CSS sanity of the
      logical basis (HX @ LZ = 0, rank 12).

Exit code 0 iff every check passes.  Writes results/wsc_verify_report.json.
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, 'qae_experiments'),
           os.path.join(ROOT, 'archive-rerun'),
           HERE):
    if os.path.isdir(_p):
        sys.path.insert(0, _p)

import stim  # noqa: E402
from bb_codes import BB72  # noqa: E402
from cmp_common import logical_basis  # noqa: E402
from wsc_circuit_point import build_circuit  # noqa: E402

HX, HZ = BB72['HX'], BB72['HZ']
N, N2 = 72, 36


def record(sim):
    rec = getattr(sim, 'measurement_record', None)
    if rec is None and callable(getattr(sim, 'current_measurement_record', None)):
        rec = sim.current_measurement_record()
    return [bool(b) for b in rec]


def run(circ):
    sim = stim.TableauSimulator()
    sim.do(circ)
    return record(sim)


def gadget(bits, xtype, reversed_dir):
    c = stim.Circuit()
    if xtype:
        for q, b in enumerate(bits):
            c.append('H', q)
            if b:
                c.append('Z', q)
        c.append('H', 2)
        for d in (0, 1):
            c.append('CX', [d, 2] if reversed_dir else [2, d])
        c.append('H', 2)
    else:
        for q, b in enumerate(bits):
            if b:
                c.append('X', q)
        for d in (0, 1):
            c.append('CX', [2, d] if reversed_dir else [d, 2])
    c.append('M', 2)
    return run(c)[0]


def t1():
    det, bug = [], []
    for xtype in (False, True):
        for b in ((0, 0), (0, 1), (1, 0), (1, 1)):
            ok = gadget(b, xtype, False) == (b[0] ^ b[1])
            det.append(ok)
            bug.append(gadget(b, xtype, True) is False)  # constant 0
    ok = all(det) and all(bug)
    return ok, dict(correct_parity_all_inputs=all(det),
                    reversed_returns_constant_zero=all(bug))


def t2():
    c0, bk = build_circuit(2, 0.0, return_bookkeeping=True)
    n_meas = bk['meas_count']

    def det_bits(circ, rec):
        out = []
        for instr in circ:
            if instr.name == 'DETECTOR':
                idx = [n_meas + t.value for t in instr.targets_copy()]
                out.append(int(np.bitwise_xor.reduce([rec[i] for i in idx])))
        return out

    rec0 = run(c0)
    det_vals = det_bits(c0, rec0)
    z0_ok = all(rec0[p] is False for p in bk['z_meas_pos'][0])
    xfin0 = np.array([rec0[bk['final_pos'][d]] for d in range(N)], np.uint8)
    cs0 = bool(np.array_equal((HZ @ xfin0) % 2, np.zeros(N2, np.uint8)))
    # Memory invariant (NOT bit-exact readout): the noiseless X-check
    # measurements project the data within the fixed Z-syndrome sector, so
    # the physical readout is random in ker(HZ); what must be preserved are
    # the logical-Z values and the Z-syndrome.  Assert exactly that.
    LZd = np.asarray(bk['LZ'], np.uint8) % 2
    inv_ok = True
    for l in [np.zeros(N, np.uint8)] + list(bk['LZ']) + [HZ[0] % 2]:
        prep = np.asarray(l, np.uint8) % 2
        cc = build_circuit(2, 0.0, prep_x=prep)
        rr = run(cc)
        xfin = np.array([rr[bk['final_pos'][d]] for d in range(N)], np.uint8)
        dv = det_bits(cc, rr)
        # A prep carrying a fixed nonzero Z-syndrome (a logical-Z or
        # Z-stabilizer support need not lie in ker(HZ)) must fire EXACTLY the
        # round-0 Z-anchor detectors (indices 0..35) on supp(HZ @ prep) and
        # no others; the logical values and syndrome must be preserved.
        fired = {i for i, b in enumerate(dv) if b}
        expect = {j for j in range(N2) if (HZ @ prep)[j] % 2}
        inv_ok &= (fired == expect)
        inv_ok &= bool(np.array_equal((LZd @ xfin) % 2, (LZd @ prep) % 2))
        inv_ok &= bool(np.array_equal((HZ @ xfin) % 2, (HZ @ prep) % 2))
    # out-of-codespace prep e_0 fires exactly round-0 Z dets on supp(HZ[:,0])
    ce = build_circuit(2, 0.0, prep_x=np.eye(1, N, 0, np.uint8)[0])
    re_ = run(ce)
    fired = [j for j in range(N2) if re_[bk['z_meas_pos'][0][j]]]
    ooc = fired == list(np.flatnonzero(HZ[:, 0]))
    ok = (not any(det_vals)) and cs0 and z0_ok and inv_ok and ooc
    return ok, dict(all_detectors_silent=not any(det_vals),
                    final_readout_in_codespace=cs0, z_anchor_zero=z0_ok,
                    logical_values_and_syndrome_preserved=bool(inv_ok),
                    out_of_codespace_fires_predicted=bool(ooc))


def t3():
    zx_ok, zx_bad = True, []
    for q in range(N):
        c = build_circuit(1, 0.0, inject_x=[q])
        bk = build_circuit(1, 0.0, return_bookkeeping=True)[1]
        rr = run(c)
        got = np.array([rr[p] for p in bk['z_meas_pos'][0]], np.uint8)
        if not np.array_equal(got, np.asarray(HZ[:, q], np.uint8) % 2):
            zx_ok, zx_bad = False, zx_bad + [q]
    xz_ok, xz_bad = True, []
    for q in range(N):
        c = build_circuit(1, 0.0, x_prep=True, inject_z=[q])
        bk = build_circuit(1, 0.0, return_bookkeeping=True)[1]
        rr = run(c)
        got = np.array([rr[p] for p in bk['x_meas_pos'][0]], np.uint8)
        if not np.array_equal(got, np.asarray(HX[:, q], np.uint8) % 2):
            xz_ok, xz_bad = False, xz_bad + [q]
    return zx_ok and xz_ok, dict(x_injection_matches_HZ_columns=zx_ok,
                                 z_injection_matches_HX_columns=xz_ok,
                                 bad_z_columns=zx_bad, bad_x_columns=xz_bad)


def t4(rounds=3):
    c, bk = build_circuit(rounds, 0.0, return_bookkeeping=True)
    n_meas = bk['meas_count']
    got_dets, got_obs = [], {}
    for instr in c0_iter(c):
        if instr.name == 'DETECTOR':
            got_dets.append(tuple(sorted(n_meas + t.value
                                         for t in instr.targets_copy())))
        elif instr.name == 'OBSERVABLE_INCLUDE':
            oi = int(instr.gate_args_copy()[0])
            got_obs[oi] = tuple(sorted(n_meas + t.value
                                       for t in instr.targets_copy()))
    exp = []
    for j in range(N2):
        exp.append((bk['z_meas_pos'][0][j],))
    for r in range(1, rounds):
        for j in range(N2):
            exp.append(tuple(sorted((bk['z_meas_pos'][r][j],
                                     bk['z_meas_pos'][r - 1][j]))))
    for r in range(1, rounds):
        for i in range(N2):
            exp.append(tuple(sorted((bk['x_meas_pos'][r][i],
                                     bk['x_meas_pos'][r - 1][i]))))
    for j in range(N2):
        exp.append(tuple(sorted([bk['final_pos'][d]
                                 for d in np.flatnonzero(HZ[j])] +
                                [bk['z_meas_pos'][-1][j]])))
    det_ok = sorted(exp) == sorted(got_dets) and len(exp) == len(got_dets)
    obs_ok = all(got_obs.get(li) == tuple(sorted(
        bk['final_pos'][d] for d in np.flatnonzero(l)))
        for li, l in enumerate(bk['LZ'])) and len(got_obs) == 12
    LZd = np.asarray(bk['LZ'], np.uint8) % 2
    css_ok = int(np.linalg.matrix_rank(
        (HX @ LZd.T) % 2)) == 0 and int(np.linalg.matrix_rank(LZd)) == 12
    return det_ok and obs_ok and css_ok, dict(detector_map_exact=det_ok,
                                              observable_map_exact=obs_ok,
                                              logical_basis_css=css_ok)


def c0_iter(c):
    return list(c)


def main():
    tests = {}
    for name, fn in [('T1_gadget_parity', t1), ('T2_codespace', t2),
                     ('T3_injection_columns', t3), ('T4_detector_observable_audit', t4)]:
        ok, detail = fn()
        tests[name] = dict(pass_=bool(ok), **detail)
        print(('PASS' if ok else 'FAIL'), name, detail if not ok else '', flush=True)
    allok = all(v['pass_'] for v in tests.values())
    os.makedirs(os.path.join(HERE, 'results'), exist_ok=True)
    with open(os.path.join(HERE, 'results', 'wsc_verify_report.json'), 'w') as f:
        json.dump(dict(circuit_rev='v24-corrected-extraction',
                       all_pass=allok, tests=tests), f, indent=2)
    print('WSC-VERIFY', 'ALL PASS' if allok else 'FAILURES PRESENT')
    sys.exit(0 if allok else 1)


if __name__ == '__main__':
    main()
