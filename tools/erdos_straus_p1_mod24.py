# tools/erdos_straus_p1_mod24.py
"""19.0.6 p ≡ 1 (mod 24) 的枚举：找 (r, c) 使 4/p = c/(p+r) + 1/m + 1/n。

方法：枚举 (r, c)，符号推导 4/p − c/(p+r)，看剩余是否能拆成两个单位分数。
"""
import sympy
from typing import Optional, Tuple, List


def try_r_c(p: int, r: int, c: int) -> Optional[Tuple[int, int, int, int]]:
    """给定 (r, c)，检查 4/p = c/(p+r) + 1/m + 1/n 是否有解。

    返回 (m, n, r, c) 或 None。
    条件：c | (p+r)，4/p − c/(p+r) > 0，且 4/p − c/(p+r) = 1/m + 1/n。
    """
    if (p + r) <= 0:
        return None
    if (p + r) % c != 0:
        return None
    diff = sympy.Rational(4, p) - sympy.Rational(c, p + r)
    if diff <= 0:
        return None
    # 拆 diff = 1/m + 1/n
    # diff = 1/m + 1/n ⟺ (diff·m − 1)(diff·n − 1) = 1？不，用标准方法：
    # 1/m + 1/n = K/N ⟺ (Km − N)(Kn − N) = N²
    # 这里 diff = K/N，K, N 是 diff 的分子分母
    K, N = diff.p, diff.q
    # 枚举 N² 的因子 d，检查 d ≡ −N (mod K)
    n2 = N * N
    for d in sympy.divisors(n2):
        if (d + N) % K != 0:
            continue
        m = (d + N) // K
        num = n2 // d + N
        if num % K != 0:
            continue
        n = num // K
        if m > 0 and n > 0:
            # 验证
            if sympy.simplify(diff - (sympy.Rational(1, m) + sympy.Rational(1, n))) == 0:
                return (m, n, r, c)
    return None


def find_construction_p1_mod24(p: int) -> Optional[Tuple[int, int, int]]:
    if p % 24 != 1:
        return None
    if not sympy.isprime(p):
        return None
    for c in [4, 8]:
        for r in range(3, 64, 4):  # r ≡ 3 (mod 4), r = 3, 7, ..., 63
            res = try_r_c(p, r, c)
            if res is not None:
                m, n, r_used, c_used = res
                x = (p + r_used) // c_used
                return (x, m, n)
    return None


def verify_p1_mod24(p: int) -> Tuple[bool, str]:
    """验证 find_construction_p1_mod24(p) 给出的 (x,y,z) 满足 4/p = 1/x+1/y+1/z。"""
    r = find_construction_p1_mod24(p)
    if r is None:
        return False, f"p={p}: 未找到构造"
    x, y, z = r
    diff = sympy.Rational(4, p) - (
        sympy.Rational(1, x) + sympy.Rational(1, y) + sympy.Rational(1, z)
    )
    if sympy.simplify(diff) != 0:
        return False, f"p={p}: 验证失败 ({x},{y},{z})"
    return True, f"p={p}: ({x},{y},{z})"


def verify_all_p1_mod24(N: int) -> dict:
    """对 p ≤ N 的 p ≡ 1 (mod 24) 素数全验证。"""
    total = 0
    passed = 0
    failed = []
    for p in range(25, N + 1, 24):
        if not sympy.isprime(p):
            continue
        total += 1
        ok, reason = verify_p1_mod24(p)
        if ok:
            passed += 1
        else:
            failed.append((p, reason))
    return {
        "total": total, "passed": passed, "failed": failed,
        "pass_rate": f"{100 * passed // max(total, 1)}%",
    }

def stats_r_c_p1_mod24(N: int) -> dict:
    from sympy import isprime
    from collections import Counter
    counter = Counter()
    total = 0
    failed_p = []
    for p in range(25, N + 1, 24):
        if not isprime(p):
            continue
        total += 1
        found = False
        for c in [4, 8]:
            for r in [1, 3, 5, 7, 9, 11, 13, 15]:
                res = try_r_c(p, r, c)
                if res is not None:
                    counter[(r, c)] += 1
                    found = True
                    break
            if found:
                break
        if not found:
            failed_p.append(p)
    return {"total": total, "counter": dict(counter), "failed": failed_p}

def stats_d_pattern(N_max: int) -> dict:
    """统计 p ≤ N_max 的 p ≡ 1 (mod 24)，成功解中 d 的模式。"""
    from sympy import isprime, factorint
    from sympy.ntheory import divisors
    from collections import Counter, defaultdict

    records = []
    for p in range(25, N_max + 1, 24):
        if not isprime(p):
            continue
        for c in [4]:
            for r in range(3, 64, 4):
                if (p + r) % c != 0:
                    continue
                diff = sympy.Rational(4, p) - sympy.Rational(c, p + r)
                if diff <= 0:
                    continue
                K, N = diff.p, diff.q
                found = False
                for d in divisors(N * N):
                    if (d + N) % K != 0:
                        continue
                    if (N * N // d + N) % K != 0:
                        continue
                    m = (d + N) // K
                    n = (N * N // d + N) // K
                    if m > 0 and n > 0:
                        records.append({
                            "p": p, "r": r, "c": c,
                            "K": K, "N": N, "d": d,
                            "d_over_N": sympy.Rational(d, N),
                            "d_factors": factorint(d),
                            "N_factors": factorint(N),
                        })
                        found = True
                        break
                if found:
                    break
            if found:
                break

    # 统计 d/N 的分布
    d_over_N_counter = Counter()
    for rec in records:
        d_over_N_counter[str(rec["d_over_N"])] += 1

    # 统计 d 是否整除 N
    d_divides_N = sum(1 for rec in records if rec["N"] % rec["d"] == 0)

    return {
        "total": len(records),
        "d_over_N_top": d_over_N_counter.most_common(20),
        "d_divides_N": d_divides_N,
        "records": records,
    }