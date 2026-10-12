#!/usr/bin/env python3
"""
stats_intervals.py — single statistical analysis module for the v24+ archive.

Every interval reported in the manuscript is generated here with an explicit
estimand, sampling unit, stopping rule, family definition, and confidence
allocation. Methods:

Fixed sample size (pinned N):
  cp_interval(k, n, alpha)        exact two-sided Clopper--Pearson
  cp_upper_zero(n, alpha)         exact one-sided zero-count UB 1-alpha^(1/n)

Sequential (pinned stopping rule, random N):
  cs_interval(k, n, alpha)        time-uniform confidence sequence for a
                                  Bernoulli mean: Robbins conjugate-mixture
                                  CS with uniform mixing distribution
                                  (Howard, Ramdas, McAuliffe, Sekhon 2021,
                                  arXiv:1810.08240, Thm. 2 corollaries;
                                  valid at arbitrary stopping times).
                                  p in CS iff  C(n,k) p^k (1-p)^{n-k}
                                  >= alpha/(n+1); boundary by bisection.

Ratio lower bounds:
  ratio_lower_exact(...)          fixed-N exact-CP based (both arms fixed-N)
  ratio_lower_cs(...)             CS-based, for adaptively stopped arms;
                                  joint >=1-alpha via alpha/2 per arm
                                  (Bonferroni over the two endpoints of the
                                  ratio only, as disclosed per table).

Coverage counterexample (review Sec. 4.3): self_check() reports the exact
coverage of a nominal 95% Wilson interval under the adaptive stopping rule
(stop at >=50 failures or 20,000 trials) at true p=0.021, computed by
enumerating the stopping-time distribution.

CLI: python stats_intervals.py --self-check
"""
from __future__ import annotations
import math
from scipy.stats import beta as beta_dist
from scipy.special import gammaln


# ---------------------------------------------------------------- fixed N --
def cp_interval(k: int, n: int, alpha: float = 0.05):
    """Exact two-sided Clopper--Pearson interval, fixed pinned n."""
    if n <= 0:
        raise ValueError("n must be positive")
    lo = 0.0 if k == 0 else float(beta_dist.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta_dist.ppf(1 - alpha / 2, k + 1, n - k))
    return lo, hi


def cp_upper_zero(n: int, alpha: float = 0.05) -> float:
    """Exact one-sided upper bound at k=0, fixed pinned n: 1-alpha^(1/n)."""
    return 1.0 - alpha ** (1.0 / n)


# ------------------------------------------------------------- sequential --
def _log_binom_pmf_unnorm(k: int, n: int, p: float) -> float:
    """log C(n,k) + k log p + (n-k) log(1-p)."""
    if p <= 0.0 or p >= 1.0:
        return -math.inf
    lc = (gammaln(n + 1) - gammaln(k + 1) - gammaln(n - k + 1))
    if k > 0:
        lc += k * math.log(p)
    if n - k > 0:
        lc += (n - k) * math.log1p(-p)
    return lc


def cs_interval(k: int, n: int, alpha: float = 0.05):
    """Robbins uniform-mixture confidence sequence at (k, n), time-uniform.

    Valid at any stopping time w.p. >= 1-alpha. The CS is the set of p with
        C(n,k) p^k (1-p)^{n-k} >= alpha/(n+1).
    """
    if not (0 <= k <= n):
        raise ValueError("need 0 <= k <= n")
    if n == 0:
        return 0.0, 1.0
    thresh = math.log(alpha / (n + 1))
    p_hat = k / n

    def logf(p):
        return _log_binom_pmf_unnorm(k, n, p)

    def solve_lo():
        # invariant: lo outside CS (logf < thresh), hi inside (logf >= thresh)
        # returns lo (just below the boundary): slightly wider, conservative
        if k == 0:
            return 0.0
        lo, hi = 1e-300, p_hat
        for _ in range(200):
            mid = math.sqrt(lo * hi)
            if logf(mid) >= thresh:
                hi = mid
            else:
                lo = mid
        return lo

    def solve_hi():
        # invariant: lo inside CS, hi outside; returns hi (just above the
        # boundary): slightly wider, conservative
        if k == n:
            return 1.0
        lo, hi = p_hat, 1.0 - 1e-15
        for _ in range(200):
            mid = (lo + hi) / 2
            if logf(mid) >= thresh:
                lo = mid
            else:
                hi = mid
        return hi

    return solve_lo(), solve_hi()


def cs_upper_zero(n: int, alpha: float = 0.05) -> float:
    """Time-uniform CS upper endpoint at k=0: 1-(alpha/(n+1))^(1/n)."""
    return 1.0 - (alpha / (n + 1)) ** (1.0 / n)


# ----------------------------------------------------------------- ratios --
def ratio_lower_exact(k_hi, n_hi, k_lo, n_lo, alpha=0.05):
    """One-sided lower bound on p_hi/p_lo, both arms fixed-N.

    Joint >=1-alpha via alpha/2 per arm: lower bound =
    CP_lo(k_hi, alpha/2) / CP_hi(k_lo, alpha/2).  If k_lo == 0 the
    denominator uses the exact one-sided UB 1-(alpha/2)^(1/n_lo).
    Returns (ratio_lower, note).
    """
    lo_hi = 0.0 if k_hi == 0 else float(beta_dist.ppf(alpha / 2, k_hi, n_hi - k_hi + 1))
    if k_lo == 0:
        hi_lo = 1.0 - (alpha / 2) ** (1.0 / n_lo)
        note = "denominator zero-count: exact one-sided CP UB"
    else:
        hi_lo = float(beta_dist.ppf(1 - alpha / 2, k_lo + 1, n_lo - k_lo))
        note = "both arms fixed-N CP"
    if hi_lo <= 0:
        return float("inf"), note + "; denominator UB=0"
    return lo_hi / hi_lo, note


def ratio_lower_cs(k_hi, n_hi, k_lo, n_lo, alpha=0.05):
    """One-sided lower bound on p_hi/p_lo for adaptively stopped arms:
    CS_lo(k_hi, alpha/2) / CS_hi(k_lo, alpha/2); joint >=1-alpha."""
    lo_hi, _ = cs_interval(k_hi, n_hi, alpha / 2)
    _, hi_lo = cs_interval(k_lo, n_lo, alpha / 2)
    if hi_lo <= 0:
        return float("inf"), "CS-based; denominator UB=0"
    return lo_hi / hi_lo, "CS-based (sequential)"


# ------------------------------------------------------------- self check --
def self_check():
    """Review counterexample: exact coverage of a nominal 95% Wilson interval
    under the adaptive stopping rule (stop at >=50 failures or N=20,000
    trials, batches of 2,000), at true p=0.021. Enumerates the stopping
    distribution exactly over batch counts."""
    from scipy.stats import binom

    def wilson(k, n, z=1.959964):
        if n == 0:
            return 0.0, 1.0
        p = k / n
        den = 1 + z * z / n
        c = p + z * z / (2 * n)
        h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
        return (c - h) / den, (c + h) / den

    p, B, cap, stop = 0.021, 2000, 20000, 50
    cover = 0.0
    total = 0.0
    # enumerate paths: batches of 2000 until >=50 failures or 10 batches
    # state: accumulated failures; distribution over (k, n) at stopping
    from collections import defaultdict
    states = {0: 1.0}
    for batches in range(1, cap // B + 1):
        nxt = defaultdict(float)
        for k, pr in states.items():
            for x in range(B + 1):
                px = binom.pmf(x, B, p)
                if px == 0:
                    continue
                k2 = k + x
                n2 = batches * B
                if k2 >= stop or batches == cap // B:
                    lo, hi = wilson(k2, n2)
                    if lo <= p <= hi:
                        cover += pr * px
                    total += pr * px
                else:
                    nxt[k2] += pr * px
        states = nxt
    print(f"Wilson-95 coverage under pinned adaptive stopping at p={p}: "
          f"{cover:.4f} (nominal 0.95)  [mass {total:.6f}]")
    # sanity: CS endpoints wider than fixed-N CP at the same (k, n)
    k, n = 60, 20000
    lo_c, hi_c = cp_interval(k, n)
    lo_s, hi_s = cs_interval(k, n)
    print(f"k={k},n={n}: CP95=[{lo_c:.5f},{hi_c:.5f}]  CS95=[{lo_s:.5f},{hi_s:.5f}]")
    assert lo_s <= lo_c + 1e-12 and hi_s >= hi_c - 1e-12
    print("monotone-widening sanity: PASS")


if __name__ == "__main__":
    import sys
    if "--self-check" in sys.argv:
        self_check()
    else:
        print("stats_intervals.py: importable module; --self-check to run checks")
