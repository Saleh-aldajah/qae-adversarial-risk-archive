"""
decoders.py  —  BP+OSD and MWPM-DEM for BB qLDPC codes.
Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290

Implementation note:
  BB qLDPC codes have non-zero logical operators, so syndromes can have
  odd parity within connected components of the syndrome graph.
  PyMatching requires even parity per component to find a perfect matching.
  Solution: add a high-weight boundary edge from every detector node, so
  any odd-parity component can resolve via the boundary.
  The boundary-edge weight is 100*|log(p/(1-p))| >> single-edge weight
  (see _build_matching, boundary_weight_factor=100), ensuring it is used
  only when genuinely needed.
"""
import math
import numpy as np
import pymatching
from ldpc import BpOsdDecoder
from bb_codes import in_rowspace, syn_from_mask

def logical_fail(ez, ex, code):
    n = code['n']
    vz = np.array([(ez>>i)&1 for i in range(n)], dtype=np.uint8)
    vx = np.array([(ex>>i)&1 for i in range(n)], dtype=np.uint8)
    return not (in_rowspace(vz, code['HZ_rref'], code['HZ_pivots']) and
                in_rowspace(vx, code['HX_rref'], code['HX_pivots']))

def arr_to_mask(arr):
    return int(sum((int(b)&1)<<i for i,b in enumerate(arr)))

def syn_array(s, nc):
    return np.array([(s>>i)&1 for i in range(nc)], dtype=np.uint8)

def bernoulli_mask(n, p, rng):
    return int(sum((1 if rng.random()<p else 0)<<i for i in range(n)))

def make_bposd(H, p):
    return BpOsdDecoder(H, error_rate=p,
                        bp_method='ms', ms_scaling_factor=0.625,
                        osd_method='osd_cs', osd_order=7, max_iter=100)

def _build_matching(H, n_data, n_checks, p, boundary_weight_factor=100.0):
    """
    Build PyMatching graph from parity-check matrix.
    - Weight-1 columns: boundary edge.
    - Weight-2 columns: direct edge.
    - Weight-3 columns (BB standard): DEM chain decomposition.
    - Global boundary edges (high weight) on all nodes to handle
      odd-parity syndromes arising from logical operators.
    """
    w = abs(math.log(p/(1-p))) if 0<p<1 else 10.0
    w_boundary = w * boundary_weight_factor
    m = pymatching.Matching()
    for j in range(n_data):
        checks = [i for i in range(n_checks) if H[i,j]]
        fid = {j}
        if not checks: continue
        elif len(checks)==1:
            m.add_boundary_edge(checks[0], weight=w, fault_ids=fid)
        elif len(checks)==2:
            m.add_edge(checks[0], checks[1], weight=w, fault_ids=fid)
        else:
            for k in range(len(checks)-1):
                m.add_edge(checks[k], checks[k+1], weight=w, fault_ids=fid)
    # Global boundary: ensures all components have even parity
    for i in range(n_checks):
        m.add_boundary_edge(i, weight=w_boundary)
    return m

def make_mwpm_dem(HX, HZ, n, n2, p):
    mz = _build_matching(HX, n, n2, p)
    mx = _build_matching(HZ, n, n2, p)
    return mz, mx

def make_spacetime_mwpm(code, rounds, p):
    n, n2 = code['n'], code['n']//2
    w = abs(math.log(p/(1-p))) if 0<p<1 else 10.0
    w_b = w * 100.0

    def build(H, n_data, n_checks, rounds, wd, wm, wb):
        m = pymatching.Matching()
        for r in range(rounds):
            for j in range(n_data):
                checks = [i for i in range(n_checks) if H[i,j]]
                det_ids = [r*n_checks+c for c in checks]
                fid = {j + r*n_data}
                if not det_ids: continue
                elif len(det_ids)==1:
                    m.add_boundary_edge(det_ids[0], weight=wd, fault_ids=fid)
                elif len(det_ids)==2:
                    m.add_edge(det_ids[0], det_ids[1], weight=wd, fault_ids=fid)
                else:
                    for k in range(len(det_ids)-1):
                        m.add_edge(det_ids[k], det_ids[k+1], weight=wd, fault_ids=fid)
        for r in range(rounds-1):
            for c in range(n_checks):
                fid = {n_data*rounds + r*n_checks + c}
                m.add_edge(r*n_checks+c, (r+1)*n_checks+c, weight=wm, fault_ids=fid)
        # Global boundary for all detector nodes
        for node in range(rounds*n_checks):
            m.add_boundary_edge(node, weight=wb)
        return m

    mz = build(code['HX'], n, n2, rounds, w, w, w_b)
    mx = build(code['HZ'], n, n2, rounds, w, w, w_b)
    return mz, mx

print(f"decoders OK — ldpc {__import__('ldpc').__version__}, "
      f"pymatching {pymatching.__version__}")
