"""
bp_guided.py  —  E6: BP-guided (correlation-aware) matching decoder.

Algorithm ("BP-reweighted MWPM"):
  1. Run min-sum BP (ldpc BpDecoder, scaling 0.625, max_iter 100) on the
     BB Tanner graph for the observed syndrome.
  2. Read the per-qubit posterior log-probability ratios
     LLR_j = log P(e_j=0 | syndrome) / P(e_j=1 | syndrome).
  3. Rebuild the SAME DEM-chain graphified detector graph used by
     MWPM-DEM (decoders._build_matching), but with per-edge weight
     w_j = |LLR_j| = |log(q_j/(1-q_j))|, q_j = sigmoid(-LLR_j) clipped
     to [1e-6, 1-1e-6]; the global odd-parity boundary edges keep the
     archive's 100x scale on the prior weight |log(p/(1-p))|.
  4. Decode with PyMatching minimum-weight perfect matching.

Unlike naive MWPM-DEM (uniform weights), the BP posteriors make the
matching syndrome-context aware: qubits BP believes likely erroneous
become cheap edges, so chain-decomposition ambiguities resolve toward
the BP-favoured fault.

Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
import math
import numpy as np
import pymatching
from ldpc import BpDecoder
from decoders import arr_to_mask

Q_CLIP = 1e-6


def _build_weighted_matching(H, n_data, n_checks, weights, boundary_weight):
    """Identical topology to decoders._build_matching but with a
    per-column weight vector instead of a uniform weight."""
    m = pymatching.Matching()
    for j in range(n_data):
        checks = [i for i in range(n_checks) if H[i, j]]
        fid = {j}
        w = float(weights[j])
        if not checks:
            continue
        elif len(checks) == 1:
            m.add_boundary_edge(checks[0], weight=w, fault_ids=fid)
        elif len(checks) == 2:
            m.add_edge(checks[0], checks[1], weight=w, fault_ids=fid)
        else:
            for k in range(len(checks) - 1):
                m.add_edge(checks[k], checks[k + 1], weight=w, fault_ids=fid)
    for i in range(n_checks):
        m.add_boundary_edge(i, weight=boundary_weight)
    return m


class BpGuidedMwpm:
    """Correlation-aware matching decoder for one side (Z or X)."""

    def __init__(self, H, p):
        self.H = H
        self.n_data = H.shape[1]
        self.n_checks = H.shape[0]
        self.bp = BpDecoder(H, error_rate=p, bp_method='ms',
                            ms_scaling_factor=0.625, max_iter=100)
        w_prior = abs(math.log(p / (1 - p))) if 0 < p < 1 else 10.0
        self.w_boundary = w_prior * 100.0

    def decode_mask(self, syn_int):
        syn = np.array([(syn_int >> i) & 1 for i in range(self.n_checks)],
                       dtype=np.uint8)
        self.bp.decode(syn)
        llr = np.asarray(self.bp.log_prob_ratios, dtype=float)
        # q_j = P(e_j=1 | syndrome); ldpc LLR = log(P(0)/P(1))
        q = 1.0 / (1.0 + np.exp(np.clip(llr, -700, 700)))
        q = np.clip(q, Q_CLIP, 1.0 - Q_CLIP)
        weights = np.abs(np.log(q / (1.0 - q)))
        weights = np.maximum(weights, 1e-9)  # PyMatching wants positive
        m = _build_weighted_matching(self.H, self.n_data, self.n_checks,
                                     weights, self.w_boundary)
        return arr_to_mask(m.decode(syn))


def make_bpgm_decoder(code, p):
    """Return f(sz_int) -> correction mask for Z errors (HX side)."""
    dec = BpGuidedMwpm(code['HX'], p)
    return dec.decode_mask
