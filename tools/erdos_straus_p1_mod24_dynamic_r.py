# tools/erdos_straus_p1_mod24_dynamic_r.py
"""20.5: 动态 r 上界实验——对每个 p，允许 r 取到 p^{1/2} 以内的最大素数。
记录未覆盖列表，并测速。
"""
import time
from sympy import isprime, nextprime
from tools.erdos_straus_p1_mod24_symbolic import branch_succeeds


def largest_prime_le(n: int) -> int:
    """返回 ≤ n 的最大素数。"""
    if n < 2:
        return 2
    return int(nextprime(n) if isprime(n) else nextprime(n - 1))  # 简化，见下


def largest_prime_leq(n: int) -> int:
    """返回 ≤ n 的最大素数。"""
    if n < 2:
        return 2
    if isprime(n):
        return n
    # 从 n-1 往下找
    m = n - 1
    while m >= 2:
        if isprime(m):
            return m
        m -= 1
    return 2


def dynamic_r_uncovered(p_max: int = 100000, r_bound: str = "sqrt"):
    """对每个 p ≤ p_max，允许 r 取到 r_bound 以内的最大素数。
    r_bound: "sqrt" 表示 p^{1/2}, "half" 表示 p/2, "p" 表示 p（平凡覆盖）。
    """
    uncovered = []
    total = 0
    t0 = time.time()

    for p in range(25, p_max + 1, 24):
        if not isprime(p):
            continue
        total += 1

        if r_bound == "sqrt":
            r_max = int(p ** 0.5)
        elif r_bound == "half":
            r_max = p // 2
        elif r_bound == "p":
            r_max = p
        else:
            raise ValueError(f"Unknown r_bound: {r_bound}")

        # 从 r_max 往下找，r ≡ 3 (mod 4) 的素数
        covered = False
        r = r_max
        while r >= 3:
            if r % 4 == 3 and isprime(r) and r < p:
                if branch_succeeds(p, r, c=4):
                    covered = True
                    break
            r -= 1
        if not covered:
            uncovered.append(p)

    elapsed = time.time() - t0
    return {
        "p_max": p_max,
        "r_bound": r_bound,
        "total_primes": total,
        "uncovered_count": len(uncovered),
        "uncovered_list": uncovered,
        "elapsed_sec": elapsed,
    }


if __name__ == "__main__":
    for bound in ["sqrt", "half"]:
        result = dynamic_r_uncovered(100000, bound)
        print(f"r_bound={bound}: p_max={result['p_max']}, "
              f"total={result['total_primes']}, "
              f"uncovered={result['uncovered_count']}, "
              f"time={result['elapsed_sec']:.2f}s")
        if result["uncovered_count"] > 0:
            print(f"  未覆盖列表（前 20）: {result['uncovered_list'][:20]}")
        print()