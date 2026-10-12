"""
kunlun_cmp.py — circuit-level comparator on the Kunlun [[18,4,4]] dataset
(Wang et al., Nat. Phys. 22, 308 (2026); Zenodo 10.5281/zenodo.17706106, CC-BY-4.0).

Uses the authors' own detector check matrices Hdec{X,Z}_{r} and per-mechanism
channel_probs for r cycles. Paired design: all decoders see identical sampled
error instances (stream seed stable_seed('KUNLUNCMP', cyc, sector)).

Decoders:
  * BP-OSD     — authors' configuration (ms, max_iter=10000, osd_cs, order 7, scaling 0)
  * BP-only    — same BP, no OSD fallback
  * MWPM-prior — chain-graphified MWPM, weights from channel priors
  * BeliefMatch— same graph, weights from BP posterior LLRs (Higgott et al. 2023)
  * Relay-BP   — IBM Relay-BP (F64 defaults) directly on Hdec with channel priors

Logical truth: HX/HZ mats stack [Hdec; 4 logical-flip rows] (verified:
HX_1[:14] == HdecX_1). Failure = any of the 4 logical flip bits mispredicted.
"""
import os, sys, csv, json, time, math, pickle, hashlib, argparse
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from cmp_common import stable_seed, wilson95  # noqa: E402

KUNLUN_PKL = os.path.join(
    ROOT, 'community', 'kunlun_extract', '18_4_4', 'Set_decoder_para_18_4_4.pkl')


def build_mwpm(H, weights, boundary_weight_factor=100.0):
    """Archive-style chain graphification with per-mechanism weights."""
    import pymatching
    n_mech = H.shape[1]
    n_chk = H.shape[0]
    m = pymatching.Matching()
    wmax = max(weights) * boundary_weight_factor if len(weights) else 1.0
    for j in range(n_mech):
        checks = np.flatnonzero(H[:, j])
        fid = {j}
        if len(checks) == 0:
            continue
        elif len(checks) == 1:
            m.add_boundary_edge(int(checks[0]), weight=weights[j], fault_ids=fid,
                           merge_strategy='independent')
        elif len(checks) == 2:
            m.add_edge(int(checks[0]), int(checks[1]), weight=weights[j],
                       fault_ids=fid, merge_strategy='independent')
        else:
            for k in range(len(checks) - 1):
                m.add_edge(int(checks[k]), int(checks[k + 1]), weight=weights[j],
                           fault_ids=fid, merge_strategy='independent')
    for i in range(n_chk):
        m.add_boundary_edge(i, weight=wmax, merge_strategy='independent')
    return m


def prior_weights(probs):
    # MWPM requires non-negative weights; clip at 0 (mechanisms with p>1/2
    # become zero-weight, matching belief-matching practice)
    eps = 1e-12
    return [max(0.0, math.log((1 - min(max(p, eps), 1 - eps)) / min(max(p, eps), 1 - eps)))
            for p in probs]


class KunlunDecoders:
    def __init__(self, Hdec, LOG, probs):
        from ldpc import BpOsdDecoder, BpDecoder
        import scipy.sparse as sp
        import relay_bp
        self.H = np.asarray(Hdec, dtype=np.uint8)
        self.LOG = np.asarray(LOG, dtype=np.uint8)
        self.probs = np.asarray(probs, dtype=np.float64)
        self.n_mech = self.H.shape[1]
        self.bposd = BpOsdDecoder(sp.csr_matrix(self.H), channel_probs=list(self.probs),
                                  max_iter=10000, bp_method='ms', ms_scaling_factor=0,
                                  osd_method='osd_cs', osd_order=7)
        self.bp = BpDecoder(sp.csr_matrix(self.H), channel_probs=list(self.probs),
                            max_iter=10000, bp_method='ms', ms_scaling_factor=0)
        self.mwpm_prior = build_mwpm(self.H, prior_weights(self.probs))
        self.relay = relay_bp.RelayDecoderF64(
            sp.csr_matrix(self.H.astype(np.float64)), error_priors=self.probs.copy())

    def _pad(self, pred):
        pred = np.asarray(pred, dtype=np.uint8)
        out = np.zeros(self.n_mech, dtype=np.uint8)
        out[:min(len(pred), self.n_mech)] = pred[:self.n_mech]
        return out

    def decode(self, name, s):
        if name == 'BP-OSD':
            return np.asarray(self.bposd.decode(s), dtype=np.uint8)
        if name == 'BP-only':
            return np.asarray(self.bp.decode(s), dtype=np.uint8)
        if name == 'MWPM-prior':
            return self._pad(self.mwpm_prior.decode(s))
        if name == 'BeliefMatch':
            self.bp.decode(s)
            llr = np.asarray(self.bp.log_prob_ratios, dtype=np.float64)
            from scipy.special import expit
            ppost = np.clip(expit(-llr), 1e-12, 1 - 1e-12)
            w = np.maximum(0.0, np.log((1 - ppost) / ppost))
            m = build_mwpm(self.H, list(w))
            return self._pad(m.decode(s))
        if name == 'Relay-BP':
            return np.asarray(self.relay.decode(s.astype(np.uint8)), dtype=np.uint8)
        raise ValueError(name)


def run_point(cyc, sector, shots, out_csv, failbits_dir):
    dec_names = ['BP-OSD', 'BP-only', 'MWPM-prior', 'BeliefMatch', 'Relay-BP']
    with open(KUNLUN_PKL, 'rb') as f:
        P = pickle.load(f)
    Hfull = P[f'H{sector}_{cyc}'].toarray().astype(np.uint8)
    Hdec = P[f'Hdec{sector}_{cyc}'].toarray().astype(np.uint8)
    n_det = Hdec.shape[0]
    assert np.array_equal(Hfull[:n_det], Hdec)
    LOG = Hfull[n_det:]
    assert LOG.shape[0] == 4
    probs = np.asarray(P[f'channel_probs{sector}_{cyc}'], dtype=np.float64)
    n_mech = Hdec.shape[1]
    assert len(probs) == n_mech

    seed = stable_seed('KUNLUNCMP', cyc, sector)
    rng = np.random.default_rng(seed)
    E = (rng.random((shots, n_mech)) < probs[None, :]).astype(np.uint8)
    S = (E @ Hdec.T) % 2          # (shots, n_det)
    A = (E @ LOG.T) % 2           # (shots, 4) actual logical flips

    dec = KunlunDecoders(Hdec, LOG, probs)
    rows = []
    for name in dec_names:
        fails = np.zeros(shots, dtype=np.uint8)
        per_log_fails = np.zeros(4, dtype=np.int64)
        t0 = time.time()
        for t in range(shots):
            c = dec.decode(name, S[t])
            flips = (LOG @ c) % 2
            bad = flips != A[t]
            if bad.any():
                fails[t] = 1
                per_log_fails += bad.astype(np.int64)
        dt = time.time() - t0
        k = int(fails.sum())
        lo, hi = wilson95(k, shots)
        row = dict(exp='kunlun_circuit_cmp', code='BB18[[18,4,4]]', decoder=name,
                   cycles=cyc, sector=sector, shots=shots, failures=k,
                   ler=round(k / shots, 6), ci_lo=round(lo, 6), ci_hi=round(hi, 6),
                   per_logical_failures=';'.join(map(str, per_log_fails)),
                   seed=seed, stream='KUNLUNCMP', sec=round(dt, 2),
                   hdec_sha256=hashlib.sha256(Hdec.tobytes()).hexdigest())
        rows.append(row)
        if failbits_dir:
            os.makedirs(failbits_dir, exist_ok=True)
            np.save(os.path.join(failbits_dir,
                                 f'kunlun_{name.replace("+","p").replace("-","m")}_{cyc}{sector}.npy'),
                    fails)
        print(f"  cyc{cyc} {sector} {name:12s}: {k:5d}/{shots} "
              f"[{lo:.4f},{hi:.4f}] ({dt:.0f}s)", flush=True)

    exists = os.path.exists(out_csv)
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    with open(out_csv, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        if not exists:
            w.writeheader()
        for r in rows:
            w.writerow(r)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cycles', nargs='+', type=int, default=[1, 3, 6])
    ap.add_argument('--sectors', nargs='+', default=['X', 'Z'])
    ap.add_argument('--shots', type=int, default=10000)
    ap.add_argument('--out', default=os.path.join(HERE, 'results', 'kunlun_cmp.csv'))
    ap.add_argument('--failbits', default=os.path.join(HERE, 'results', 'failbits'))
    args = ap.parse_args()
    t0 = time.time()
    for cyc in args.cycles:
        for sector in args.sectors:
            run_point(cyc, sector, args.shots, args.out, args.failbits)
    print(f"kunlun comparator done in {time.time()-t0:.0f}s")


if __name__ == '__main__':
    main()
