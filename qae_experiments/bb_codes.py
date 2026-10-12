"""
bb_codes.py  —  BB[[72,12,6]] and BB[[144,12,12]] construction.
Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
import hashlib, itertools
import numpy as np

def gf2_rank(M):
    A = M.copy() & 1
    m, n = A.shape
    rank = 0
    for c in range(n):
        piv = next((r for r in range(rank, m) if A[r, c]), None)
        if piv is None: continue
        A[[rank, piv]] = A[[piv, rank]]
        for r in range(m):
            if r != rank and A[r, c]: A[r] ^= A[rank]
        rank += 1
    return rank

def gf2_rref(M):
    A = M.copy() & 1
    m, n = A.shape
    rank, pivots = 0, []
    for c in range(n):
        piv = next((r for r in range(rank, m) if A[r, c]), None)
        if piv is None: continue
        A[[rank, piv]] = A[[piv, rank]]
        for r in range(m):
            if r != rank and A[r, c]: A[r] ^= A[rank]
        pivots.append(c); rank += 1
    return A[:rank], pivots

def in_rowspace(v, rref, pivots):
    v = v.copy() & 1
    for row, col in zip(rref, pivots):
        if v[col]: v ^= row
    return not v.any()

def col_syns(H):
    m, n = H.shape
    return [int(sum((int(H[i,j])&1) << i for i in range(m))) for j in range(n)]

def syn_from_mask(mask, cs):
    s = 0
    while mask:
        lsb = mask & -mask
        s ^= cs[lsb.bit_length()-1]
        mask ^= lsb
    return s

def sha256_matrix(M):
    return hashlib.sha256(M.astype(np.uint8).tobytes()).hexdigest()

def build_bb(ell, m, a_exp, b_exp):
    Il = np.eye(ell, dtype=np.uint8)
    Im = np.eye(m,   dtype=np.uint8)
    x = {i: np.kron(np.roll(Il, i, 1), Im) for i in range(ell)}
    y = {i: np.kron(Il, np.roll(Im, i, 1)) for i in range(m)}
    a0,a1,a2 = a_exp
    b0,b1,b2 = b_exp
    A = (x[a0]^y[a1]^y[a2]).astype(np.uint8)
    B = (y[b0]^x[b1]^x[b2]).astype(np.uint8)
    HX = np.hstack([A, B]).astype(np.uint8)
    HZ = np.hstack([B.T, A.T]).astype(np.uint8)
    n  = 2*ell*m
    rx = gf2_rank(HX)
    rz = gf2_rank(HZ)
    k  = n - rx - rz
    HX_rref, HX_pivots = gf2_rref(HX)
    HZ_rref, HZ_pivots = gf2_rref(HZ)
    return dict(ell=ell, m=m, n=n, k=k, rx=rx, rz=rz,
                HX=HX, HZ=HZ,
                HX_rref=HX_rref, HX_pivots=HX_pivots,
                HZ_rref=HZ_rref, HZ_pivots=HZ_pivots,
                hx_cols=col_syns(HX), hz_cols=col_syns(HZ),
                hx_sha=sha256_matrix(HX), hz_sha=sha256_matrix(HZ))

BB72  = build_bb(6,  6, (3,1,2), (3,1,2))
BB144 = build_bb(12, 6, (3,1,2), (3,1,2))

for code, name in [(BB72,'BB72'),(BB144,'BB144')]:
    comm = np.all(((code['HX'] @ code['HZ'].T)&1)==0)
    print(f"{name}: n={code['n']} k={code['k']} rx={code['rx']} rz={code['rz']} "
          f"commutation={'PASS' if comm else 'FAIL'}")
    print(f"  HX sha256: {code['hx_sha'][:32]}...")
    print(f"  HZ sha256: {code['hz_sha'][:32]}...")

# BB288 — added for v5/v6 three-code finite-size study
# Parameters from Bravyi et al. (2024), Table 1:
#   ell=12, m=12, A=x^3+y^2+y^7, B=y^3+x+x^2
BB288 = build_bb(12, 12, (3, 2, 7), (3, 1, 2))
