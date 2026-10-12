"""
cmp_common.py — shared construction for the BB72 modern-decoder comparator grid.

Protocol (pinned, mirrors archive-rerun/run_single_round_only.py):
  * p grid PS_STD, TRIALS trials per point
  * per trial: ez = first 72 Bernoulli(p) draws, ex = next 72 draws
    (bit-identical to archive bernoulli_mask loop; vectorized draw verified
     to produce the same PCG64 stream)
  * Z-sector: ez decoded with HX ; X-sector: ex decoded with HZ
  * trial fails if EITHER sector logical-fails
  * comparator stream seed = stable_seed("COMPARE", "BB72", p)  -> every decoder
    sees IDENTICAL error instances (paired design, enables McNemar statistics)

Equivalence: symatch GTCode matrices == archive BB72 matrices under the explicit
column permutation `perm` (rows identical), certified in
active_provenance/results/bb72_symatch_equiv_cert.json.

Symatch sector handling: SyMatch decodes X-type errors via gtcode.hz.
For the Z-sector we build a deep-copied GTCode with hx/hz swapped and the
X-logical basis injected (same linear-algebra recipe, native decoding).
"""
import sys, os, copy, hashlib, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'symatch_repo', 'src'))
sys.path.insert(0, os.path.join(ROOT, 'archive-rerun'))
sys.path.insert(0, os.path.join(ROOT, 'qae_experiments'))

from bb_codes import BB72, gf2_rref, in_rowspace  # noqa: E402

# The public symatch release references check_all_subsyms0 (the L/R-only
# predecode consistency test) but never defines it. We reimplement it per
# the paper's §III description: a syndrome is consistent with an RL-only
# error pattern iff it is orthogonal to every subsymmetry (check-relation)
# of the orientation-restricted PCM. Vacuously True when no subsymmetries.
import symatch_prep as _smp  # noqa: E402

if not hasattr(_smp, 'check_all_subsyms0'):
    def _check_all_subsyms0(subsyms, syndrome):
        subsyms = np.asarray(subsyms)
        if subsyms.size == 0:
            return True
        return not np.any((subsyms @ np.asarray(syndrome)) % 2)
    _smp.check_all_subsyms0 = _check_all_subsyms0

PS_STD = [0.001, 0.002, 0.004, 0.006, 0.008, 0.010, 0.012]
TRIALS = 10000


def stable_seed(*args):
    key = "|".join(str(a) for a in args).encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:4], 'big')


def wilson95(k, n):
    import math
    if n == 0:
        return 0., 1.
    z = 1.96
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0., c - m), min(1., c + m)


# ---------------------------------------------------------------- GF(2) tools
def gf2_kernel_basis(H):
    """basis vectors of ker(H) via RREF (rows of output)."""
    A = np.array(H, dtype=np.uint8) % 2
    m, n = A.shape
    r = 0
    pivots = []
    for c in range(n):
        rows = np.nonzero(A[r:, c])[0]
        if len(rows) == 0:
            continue
        p = r + rows[0]
        if p != r:
            A[[r, p]] = A[[p, r]]
        mask = np.nonzero(A[:, c])[0]
        mask = mask[mask != r]
        if len(mask):
            A[mask] = A[mask] ^ A[r]
        pivots.append(c)
        r += 1
        if r == m:
            break
    piv = set(pivots)
    free = [c for c in range(n) if c not in piv]
    ker = []
    for f in free:
        v = np.zeros(n, dtype=np.uint8)
        v[f] = 1
        for i, pc in enumerate(sorted(piv)):
            if A[i, f]:
                v[pc] = 1
        ker.append(v)
    return np.array(ker, dtype=np.uint8)


def logical_basis(HX, HZ, k):
    """basis of ker(HX) mod row(HZ): k Z-logical operators (rows)."""
    ker = gf2_kernel_basis(HX)
    basis = np.array(HZ, dtype=np.uint8)
    br, bp = gf2_rref(basis)
    logs = []
    for v in ker:
        cand = np.vstack([basis, v])
        cr, cp = gf2_rref(cand)
        if len(cp) > len(bp):
            logs.append(v)
            basis = cand
            br, bp = cr, cp
            if len(logs) == k:
                break
    return np.array(logs, dtype=np.uint8)


# ------------------------------------------------- symatch code construction
def build_gross_pair():
    """Return (gross_Z, gross_X, OBS_Z, OBS_X, perm):
    gross_Z: GTCode with native hz (=archive HZ up to perm) + injected Z-logicals
    gross_X: deep copy with hx/hz swapped + injected X-logicals (for Z-error sector)
    perm: archive column -> symatch column
    """
    from gentoriccode import GTCode

    gross = GTCode(v1=[12, 0], v2=[0, 12], basis='Z',
                   fpoly=[[3, 0], [0, 1], [0, 2]], gpoly=[[0, 3], [1, 0], [2, 0]],
                   pphys=0.001, addwidth=0.1, coi=False)

    def arc2sym(c):
        if c < 36:
            i, j = c // 6, c % 6
            return 12 * i + j
        i, j = (c - 36) // 6, (c - 36) % 6
        return 12 * i + 11 if j == 0 else 12 * i + 5 + j

    perm = np.array([arc2sym(c) for c in range(72)])
    HX_s = gross.hx.astype(np.uint8)
    HZ_s = gross.hz.astype(np.uint8)
    assert np.array_equal(HX_s[:, perm], BB72['HX'])
    assert np.array_equal(HZ_s[:, perm], BB72['HZ'])

    LZ = logical_basis(HX_s, HZ_s, 12)   # Z-logicals (pair with X errors)
    LX = logical_basis(HZ_s, HX_s, 12)   # X-logicals (pair with Z errors)

    gross.vert_zlogs = {i: LZ[i] for i in range(6)}
    gross.horz_zlogs = {i: LZ[6 + i] for i in range(6)}
    gross.bcode_hlogs = None
    gross.dcode = None
    gross.d = 6

    grossX = copy.deepcopy(gross)
    grossX.hx = HZ_s.copy()   # swapped
    grossX.hz = HX_s.copy()   # decoder pcm role now played by HX
    # recompute z_syms for the swapped hz
    from utils import row_echelon_form
    _, cmatz = row_echelon_form(grossX.hz)
    grossX.z_syms = np.array(cmatz[(grossX.N // 2) - (grossX.ldpccode.K // 2):, :].copy())
    grossX.vert_zlogs = {i: LX[i] for i in range(6)}
    grossX.horz_zlogs = {i: LX[6 + i] for i in range(6)}
    grossX.bcode_hlogs = None
    grossX.dcode = None
    grossX.d = 6
    return gross, grossX, LZ, LX, perm


# ------------------------------------------------------------- decoder faces
class CmpDecoder:
    """Uniform face: decode_z(s36)->c72-or-flips, decode_x(s36) ; fail criteria."""

    name = 'base'
    paired_flips = False  # True for symatch (flip-predicting)

    def decode_x(self, s):
        raise NotImplementedError

    def decode_z(self, s):
        raise NotImplementedError

    def fail_x(self, ex, pred):
        raise NotImplementedError

    def fail_z(self, ez, pred):
        raise NotImplementedError


class BpOsdCmp(CmpDecoder):
    name = 'BP+OSD'

    def __init__(self, p):
        from ldpc import BpOsdDecoder
        kw = dict(bp_method='ms', ms_scaling_factor=0.625,
                  osd_method='osd_cs', osd_order=7, max_iter=100)
        self.dz = BpOsdDecoder(BB72['HX'], error_rate=p, **kw)
        self.dx = BpOsdDecoder(BB72['HZ'], error_rate=p, **kw)
        self.HXr, self.HXp = BB72['HX_rref'], BB72['HX_pivots']
        self.HZr, self.HZp = BB72['HZ_rref'], BB72['HZ_pivots']

    def decode_x(self, s):
        return np.asarray(self.dx.decode(s), dtype=np.uint8)

    def decode_z(self, s):
        return np.asarray(self.dz.decode(s), dtype=np.uint8)

    def fail_x(self, ex, pred):
        return not in_rowspace(ex ^ pred, self.HXr, self.HXp)

    def fail_z(self, ez, pred):
        return not in_rowspace(ez ^ pred, self.HZr, self.HZp)


class RelayCmp(CmpDecoder):
    name = 'Relay-BP'

    def __init__(self, p):
        import scipy.sparse as sp
        import relay_bp
        self.dz = relay_bp.RelayDecoderF64(
            sp.csr_matrix(BB72['HX'].astype(np.float64)),
            error_priors=np.full(72, p))
        self.dx = relay_bp.RelayDecoderF64(
            sp.csr_matrix(BB72['HZ'].astype(np.float64)),
            error_priors=np.full(72, p))
        self.HXr, self.HXp = BB72['HX_rref'], BB72['HX_pivots']
        self.HZr, self.HZp = BB72['HZ_rref'], BB72['HZ_pivots']

    def decode_x(self, s):
        return np.asarray(self.dx.decode(s.astype(np.uint8)), dtype=np.uint8)

    def decode_z(self, s):
        return np.asarray(self.dz.decode(s.astype(np.uint8)), dtype=np.uint8)

    def fail_x(self, ex, pred):
        return not in_rowspace(ex ^ pred, self.HXr, self.HXp)

    def fail_z(self, ez, pred):
        return not in_rowspace(ez ^ pred, self.HZr, self.HZp)


class SymatchCmp(CmpDecoder):
    """flip-predicting; failure = predicted flip vector != actual flip vector."""
    paired_flips = True

    def __init__(self, p, bp=False, predecode=False, simplex=False, tag=None):
        from symatch_prep import SyMatch
        if not hasattr(SymatchCmp, '_built'):
            (SymatchCmp._gZ, SymatchCmp._gX,
             SymatchCmp._LZ, SymatchCmp._LX,
             SymatchCmp._perm) = build_gross_pair()
            SymatchCmp._built = True
        self.perm = SymatchCmp._perm
        self.LZ, self.LX = SymatchCmp._LZ, SymatchCmp._LX
        dem = SymatchCmp._gZ.circ.detector_error_model()
        self.smx = SyMatch(SymatchCmp._gZ, dem, bp=bp, predecode=predecode,
                           simplex=simplex)
        self.smz = SyMatch(SymatchCmp._gX, dem, bp=bp, predecode=predecode,
                           simplex=simplex)
        self.name = tag or f"symatch(bp={int(bp)},pre={int(predecode)},sx={int(simplex)})"

    def _to_sym(self, e_arc):
        e_sym = np.empty(72, dtype=np.uint8)
        e_sym[self.perm] = e_arc
        return e_sym

    def decode_x(self, s):
        return np.asarray(self.smx.decode(s), dtype=np.uint8)

    def decode_z(self, s):
        return np.asarray(self.smz.decode(s), dtype=np.uint8)

    def fail_x(self, ex, pred):
        actual = (self.LZ @ self._to_sym(ex)) % 2
        return not np.array_equal(pred, actual)

    def fail_z(self, ez, pred):
        actual = (self.LX @ self._to_sym(ez)) % 2
        return not np.array_equal(pred, actual)


DECODER_SPECS = {
    'bposd':           lambda p: BpOsdCmp(p),
    'relay':           lambda p: RelayCmp(p),
    'sym_bare':        lambda p: SymatchCmp(p, bp=False, predecode=False, simplex=False,
                                            tag='symatch-bare'),
    'sym_simplex':     lambda p: SymatchCmp(p, bp=False, predecode=False, simplex=True,
                                            tag='symatch-simplex'),
    'sym_pre_simplex': lambda p: SymatchCmp(p, bp=False, predecode=True, simplex=True,
                                            tag='symatch-pre+simplex'),
    'sym_bp_simplex':  lambda p: SymatchCmp(p, bp=True, predecode=False, simplex=True,
                                            tag='symatch-BP+simplex'),
    'sym_bp_pre_simplex': lambda p: SymatchCmp(p, bp=True, predecode=True, simplex=True,
                                               tag='symatch-BP+pre+simplex'),
}


# ------------------------------------------------------------- trial streams
def trial_errors(p, trials=TRIALS):
    """(trials,72) uint8 ez and ex arrays; bit-identical to archive stream."""
    seed = stable_seed("COMPARE", "BB72", p)
    rng = np.random.default_rng(seed)
    R = rng.random((trials, 144))
    ez = (R[:, :72] < p).astype(np.uint8)
    ex = (R[:, 72:] < p).astype(np.uint8)
    return ez, ex, seed
