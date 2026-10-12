#!/usr/bin/env python3
"""
run_twirling_residual.py  —  coherent-vs-Pauli residual of the logical
channel for the canonical REP3 bit-flip memory (Limitations items on the
Proposition prop:bridge epsilon_FT <= 2 LFR bridge and the diamond-norm
proxy).

Physical noise: coherent rotation U = exp(-i theta X) on each of the 3
data qubits (the coherent analog of the bit-flip channel with
p = sin^2 theta).  Ideal syndrome extraction + majority-vote recovery.
We compute, per theta:

  p_coh    exact logical failure rate (logical X-flip probability on
           |0_L> after noise + recovery, coherent noise),
  p_tw     logical failure rate under the Pauli-twirled physical noise
           (independent bit flips, p = sin^2 theta) with the same
           recovery = 3 p^2 (1-p) + p^3,
  theta_L  coherent rotation angle of the effective logical channel
           (from its Pauli transfer matrix),
  D_twich  || E_L - E_L^twirl ||_diamond -- the twirling residual
           (Watrous variational form, entangled-input maximisation),
  D_id     || E_L - id ||_diamond -- the fault-tolerance error
           epsilon_FT of Proposition prop:bridge,
  ratio    D_id / (2 p_coh) -- the observed bridge ratio; for the
           Pauli-twirled channel prop:bridge gives ratio <= 1, while the
           coherent channel's ratio quantifies the twirling gap.

The claim checked: the bridge epsilon_FT <= 2 LFR is conservative but
tight to within a small constant across the relevant noise range, and
the coherent residual vanishes cubically (theta_L ~ theta^3), i.e. the
Pauli-channel assumption of prop:bridge costs only a bounded factor.

Output: data/twirling_residual.csv
Seeds: none (deterministic linear algebra).

Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
import numpy as np
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from qae_utils import write_csv

I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)

# REP3 bit-flip code: logical |0_L> = |000>, |1_L> = |111>.
P0 = np.zeros((8, 8)); P0[0, 0] = 1          # |000><000|
P1 = np.zeros((8, 8)); P1[7, 7] = 1          # |111><111|
ENC = np.zeros((8, 2), dtype=complex)
ENC[0, 0] = 1; ENC[7, 1] = 1                 # isometry V: |i> -> |i_L>

# Majority-vote recovery as a CPTP map: for each syndrome subspace,
# apply the correcting X on the faulting qubit, then decode.
# Kraus operators of the recovery channel R (8 -> 2 dimensional):
# syndrome projectors with correction, followed by logical readout.
def recovery_kraus():
    Ks = []
    # weight-0: |000>,|111> -> identity
    K = np.zeros((2, 8), dtype=complex); K[0, 0] = 1; K[1, 7] = 1
    Ks.append(K)
    # weight-1 syndromes: flip back qubit 1/2/3
    pairs = [(1, 0), (2, 1), (4, 2)]   # basis index of single-flip states
    for lo, q in pairs:
        hi = 7 - lo
        K = np.zeros((2, 8), dtype=complex); K[0, lo] = 1; K[1, hi] = 1
        Ks.append(K)
    return Ks

REC = recovery_kraus()

def logical_channel(theta):
    """Effective single-qubit logical channel under coherent noise."""
    U = np.cos(theta) * I2 - 1j * np.sin(theta) * X
    U3 = np.kron(np.kron(U, U), U)
    def apply(rho_L):
        rho = ENC @ rho_L @ ENC.conj().T
        rho = U3 @ rho @ U3.conj().T
        out = np.zeros((2, 2), dtype=complex)
        for K in REC:
            out += K @ rho @ K.conj().T
        return out
    return apply

def ptm(apply):
    """Pauli transfer matrix of a single-qubit channel."""
    P = [I2, X, np.array([[0, -1j], [1j, 0]]), Z]
    R = np.zeros((4, 4))
    for j in range(4):
        out = apply(P[j] / 1.0)
        for i in range(4):
            R[i, j] = 0.5 * np.trace(P[i] @ out).real
    return R

def logical_angle(R):
    """Rotation angle of the logical channel about X from its PTM
    (y-z block)."""
    a, b, c, d = R[2, 2], R[2, 3], R[3, 2], R[3, 3]
    return 0.5 * np.arctan2(b - c, a + d)

PAULIS = [I2, X, np.array([[0, -1j], [1j, 0]], dtype=complex), Z]

def delta_map_from_ptm(D):
    """Action of a PTM difference D on a 2x2 density-like operator."""
    def apply(rho):
        out = np.zeros((2, 2), dtype=complex)
        for j in range(4):
            cj = 0.5 * np.trace(PAULIS[j] @ rho)
            for i in range(4):
                out += D[i, j] * cj * PAULIS[i]
        return out
    return apply

def diamond_norm_of_difference(R, R_ref, seed=20260924):
    """||E - E_ref||_diamond via the Watrous variational form: maximise the
    output trace norm over pure two-qubit input states with a one-qubit
    reference (deterministic grids + seeded random refinement)."""
    Dm = delta_map_from_ptm(R - R_ref)

    def rand_qubit(rng):
        z = rng.normal(size=2) + 1j * rng.normal(size=2)
        return (z / np.linalg.norm(z)).astype(complex)

    def out_tracenorm(s, phi, u, v):
        psi = np.sqrt(1 - s) * np.kron([1, 0], u) \
            + np.sqrt(s) * np.exp(1j * phi) * np.kron([0, 1], v)
        rho = np.outer(psi, psi.conj()).reshape(4, 4)
        out = np.zeros((4, 4), dtype=complex)
        for a in range(4):
            for b in range(4):
                cab = 0.25 * np.trace(np.kron(PAULIS[a], PAULIS[b]) @ rho)
                if abs(cab) < 1e-15:
                    continue
                out += np.kron(PAULIS[a], Dm(PAULIS[b])) * cab
        ev = np.linalg.eigvalsh((out + out.conj().T) / 2)
        return float(np.abs(ev).sum())

    best = 0.0
    rng = np.random.default_rng(seed)
    for s in np.linspace(0, 1, 21):
        for phi in np.linspace(0, np.pi, 5):
            for _ in range(20):
                val = out_tracenorm(s, phi, rand_qubit(rng), rand_qubit(rng))
                if val > best:
                    best = val
    for _ in range(6_000):
        val = out_tracenorm(rng.random(), rng.random() * np.pi,
                            rand_qubit(rng), rand_qubit(rng))
        if val > best:
            best = val
    return best


def diamond_dist_to_twirl(R):
    """||E_L - E_L^twirl||_diamond (twirling residual of the logical
    channel)."""
    R_tw = np.zeros_like(R)
    R_tw[0, 0] = 1.0
    R_tw[1, 1] = R[1, 1]
    R_tw[2, 2] = 0.5 * (R[2, 2] + R[3, 3])
    R_tw[3, 3] = R_tw[2, 2]
    return diamond_norm_of_difference(R, R_tw)


def diamond_dist_to_id(R):
    """||E_L - id||_diamond -- the fault-tolerance error epsilon_FT."""
    return diamond_norm_of_difference(R, np.eye(4), seed=20260925)


rows = []
print(f"{'theta':>7s} {'p_coh':>10s} {'p_tw':>10s} {'ratio':>7s} "
      f"{'thL/th^3':>9s} {'D_twirl':>10s} {'D_id':>10s} {'D_id/2pL':>9s}")
for theta in [0.02, 0.04, 0.06, 0.08, 0.10, 0.15, 0.20, 0.30]:
    apply = logical_channel(theta)
    R = ptm(apply)
    rho0 = apply(np.array([[1, 0], [0, 0]], dtype=complex))
    p_coh = rho0[1, 1].real
    p = np.sin(theta) ** 2
    p_tw = 3 * p * p * (1 - p) + p ** 3
    thL = logical_angle(R)
    Dtw = diamond_dist_to_twirl(R)
    Did = diamond_dist_to_id(R)
    ratio = p_coh / p_tw if p_tw > 0 else float('nan')
    cub = thL / theta ** 3
    bratio = Did / (2 * p_coh) if p_coh > 0 else float('nan')
    rows.append(dict(theta=theta, p_sin2=round(p, 8),
                     p_l_coh=round(p_coh, 8), p_l_twirl=round(p_tw, 8),
                     ratio_coh_twirl=round(ratio, 4),
                     theta_L=round(thL, 8),
                     theta_L_over_theta3=round(cub, 4),
                     diamond_to_twirl=round(Dtw, 8),
                     diamond_to_id=round(Did, 8),
                     bridge_ratio_Did_over_2pL=round(bratio, 3)))
    print(f"{theta:7.2f} {p_coh:10.6f} {p_tw:10.6f} {ratio:7.3f} "
          f"{cub:9.3f} {Dtw:10.6f} {Did:10.6f} {bratio:9.2f}", flush=True)

write_csv('twirling_residual.csv', rows)
print('DONE twirling-residual study')
