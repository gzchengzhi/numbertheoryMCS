# tools/erdos_straus_p13_mod24.py
"""19.0.5 p ≡ 13 (mod 24) 的 Erdős–Straus 三项分解。

公式：
  4/p = 4/(p+3) + 24/(p(p+2)(p+3)) + 12/((p+2)(p+3))
  即 (x, y, z) = ((p+3)/4, p(p+2)(p+3)/24, (p+2)(p+3)/12)

前提：p ≡ 13 (mod 24) 素数。
  - 4 | p+3（p ≡ 1 mod 4）
  - 3 | p+2（p ≡ 1 mod 3）
  - 8 | p+3（p ≡ 5 mod 8，p ≡ 13 mod 24 保证）
  - 12 | (p+2)(p+3)
"""
import sympy
from typing import Optional, Tuple


def construction_p13_mod24(p: int) -> Optional[Tuple[int, int, int]]:
    if p % 24 != 13:
        return None
    if not sympy.isprime(p):
        return None
    x = (p + 3) // 4
    y = p * (p + 2) * (p + 3) // 24
    z = (p + 2) * (p + 3) // 12
    return (x, y, z)


def verify_p13_mod24(p: int) -> Tuple[bool, str]:
    r = construction_p13_mod24(p)
    if r is None:
        return False, f"p={p} 不满足 p ≡ 13 (mod 24) 或非素数"
    x, y, z = r
    diff = sympy.Rational(4, p) - (
        sympy.Rational(1, x) + sympy.Rational(1, y) + sympy.Rational(1, z)
    )
    if sympy.simplify(diff) != 0:
        return False, f"p={p}: 失败 (x={x}, y={y}, z={z})"
    return True, f"p={p}: ({x}, {y}, {z})"


def verify_all_p13_mod24(N: int) -> dict:
    total = 0
    passed = 0
    failed = []
    for p in range(13, N + 1, 24):
        if not sympy.isprime(p):
            continue
        total += 1
        ok, reason = verify_p13_mod24(p)
        if ok:
            passed += 1
        else:
            failed.append((p, reason))
    return {
        "total": total, "passed": passed, "failed": failed,
        "pass_rate": f"{100 * passed // max(total, 1)}%",
    }