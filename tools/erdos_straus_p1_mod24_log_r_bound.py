# tools/erdos_straus_p1_mod24_log_r_bound.py
"""20.6: 测试 r ≤ C * ln(p) 上界的覆盖率。"""
import time
import math
from sympy import isprime, primerange
from tools.erdos_straus_p1_mod24_symbolic import branch_succeeds


def log_r_uncovered(p_max: int, C: float = 100.0):
    """对每个 p ≤ p_max，允许 r ≤ C * ln(p)，记录未覆盖列表。"""
    uncovered = []
    total = 0
    t0 = time.time()

    for p in range(25, p_max + 1, 24):
        if not isprime(p):
            continue
        total += 1

        r_max = int(C * math.log(p))
        r_list = [r for r in primerange(3, min(r_max + 1, p)) if r % 4 == 3]
        r_list.reverse()  # 从大到小，优先试大的 r

        covered = any(branch_succeeds(p, r, c=4) for r in r_list)
        if not covered:
            uncovered.append(p)

    elapsed = time.time() - t0
    return {
        "p_max": p_max, "C": C,
        "total_primes": total, "uncovered_count": len(uncovered),
        "uncovered_list": uncovered[:20],  # 只保存前 20 个
        "elapsed_sec": elapsed,
    }


if __name__ == "__main__":
    for C in [10, 50, 100]:
        result = log_r_uncovered(100000, C)
        print(f"C={C}: p_max={result['p_max']}, "
              f"total={result['total_primes']}, "
              f"uncovered={result['uncovered_count']}, "
              f"time={result['elapsed_sec']:.2f}s")
        if result["uncovered_count"] > 0:
            print(f"  未覆盖列表（前 20）: {result['uncovered_list']}")
        print()