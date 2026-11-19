# tools/erdos_straus_p1_mod24_symbolic.py
"""20.0: p ≡ 1 (mod 24) 的真实 d 存在性检查与实测 F_r。

纪律：
  - 不假设二次特征能刻画 d 的存在性（Lemma 3 被 p=97,r=23 反例否定）。
  - 只做真实 d 的检查（无幻觉）。
"""
from typing import Tuple, List
from sympy import gcd, divisors


def compute_g_K_N(p: int, r: int, c: int = 4) -> Tuple[int, int, int]:
    """论文 §2.1: g_r = gcd(c, r·p·(p+r)), K_r = c·r/g_r, N_r = p(p+r)/g_r。"""
    g = gcd(c, r * p * (p + r))
    K = (c * r) // g
    N = (p * (p + r)) // g
    return int(g), int(K), int(N)


def branch_succeeds(p: int, r: int, c: int = 4) -> bool:
    """真实检查：是否存在 d | N^2 使得 d ≡ -N (mod K) 且 N^2/d ≡ -N (mod K)。

    这是 Lemma 2 的直接实现，无任何二次特征假设。
    """
    g, K, N = compute_g_K_N(p, r, c)
    n2 = N * N
    for d in divisors(n2):
        if (d + N) % K == 0 and (n2 // d + N) % K == 0:
            return True
    return False


def compute_failure_set(r: int, c: int = 4, p_max: int = 100000) -> List[int]:
    """实测 F_r = {a ∈ (Z/rZ)^× : 存在 p ≡ a (mod r), p ≡ 1 (mod 24) 使 branch_succeeds=False}。

    用实际 p 枚举，不依赖简化假设。p_max=100000 足够覆盖 r ≤ 23 的所有类。
    """
    from sympy import isprime
    if r < 3 or r % 4 != 3:
        return []
    failure = set()
    for p in range(25, p_max + 1, 24):
        if not isprime(p) or p % r == 0:
            continue
        a = p % r
        if a in failure:
            continue
        if not branch_succeeds(p, r, c):
            failure.add(a)
    return sorted(failure)


def density_zero_theorem_record() -> dict:
    """20.0.3：大筛法密度 0 的记录（不声称全称）。"""
    return {
        "neuron": "NEURON::S::uncovered_density_zero::p1_mod24",
        "type": "single",
        "lower": [
            ["large_sieve", ["gallagher"]],
            ["failure_rate_lt_one", ["r", "3mod4"]],
        ],
        "mediator": None,
        "anchor": None,
        "head_pattern": [
            "asymptotic_density",
            ["uncovered_set_p1_mod24", "0"],
        ],
        "N": 1,
        "weight": 1.0,
        "note": "引用 Gallagher 大筛法；不声称例外集为空，只声称密度 0。",
    }