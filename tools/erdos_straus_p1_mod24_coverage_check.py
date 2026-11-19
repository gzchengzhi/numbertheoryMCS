# tools/erdos_straus_p1_mod24_coverage_check.py
"""20.1: 检查 p_max 是否覆盖 r 的所有非零剩余类。"""
from sympy import isprime
from collections import defaultdict


def check_coverage(r: int, p_max: int = 100000) -> dict:
    """对 p ≤ p_max, p ≡ 1 (mod 24)，统计每个 a = p mod r 的出现次数。"""
    counts = defaultdict(int)
    for p in range(25, p_max + 1, 24):
        if not isprime(p):
            continue
        a = p % r
        if a != 0:
            counts[a] += 1
    all_classes = set(range(1, r))
    covered = set(counts.keys())
    missing = all_classes - covered
    return {
        "r": r,
        "p_max": p_max,
        "covered": len(covered),
        "total_classes": r - 1,
        "missing": sorted(missing),
        "min_count": min(counts.values()) if counts else 0,
    }


if __name__ == "__main__":
    for r in [3, 7, 11, 23, 31, 39, 43, 47]:
        info = check_coverage(r)
        print(f"r={r}: 覆盖 {info['covered']}/{info['total_classes']} 类, "
              f"缺失 {info['missing']}, 每类最少出现 {info['min_count']} 次")