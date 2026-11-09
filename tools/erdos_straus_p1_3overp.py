# tools/erdos_straus_p1_3overp.py
"""19.0.4 p ≡ 5 (mod 12) 的 Erdős–Straus 证明：1/p + 3/p 路径。

数学：
  p ≡ 5 (mod 12) ⟹ p ≡ 1 (mod 4) 且 p ≡ 2 (mod 3)。
  3/p = 1/x + 1/y 的充要条件 (3x-p)(3y-p) = p²。
  取 d = 1：x = (p+1)/3, y = p(p+1)/3（p ≡ 2 mod 3 时整数）。
  4/p = 1/p + 3/p = 1/p + 1/x + 1/y（三项）。

纪律：
  - 不 import 18.0 稳定层
  - 只用 sympy + numtheory_prover 的公开 parse_goal
"""
import sympy
from typing import Optional, Tuple


def construction_p5_mod12(p: int) -> Optional[Tuple[int, int, int]]:
    """p ≡ 5 (mod 12) 素数，返回 (p, x, y) 使 4/p = 1/p + 1/x + 1/y。

    返回 None 若 p 不满足条件。
    """
    if p % 12 != 5:
        return None
    if not sympy.isprime(p):
        return None
    x = (p + 1) // 3
    y = p * (p + 1) // 3
    return (p, x, y)


def verify_p5_mod12(p: int) -> Tuple[bool, str]:
    """验证 4/p = 1/p + 1/x + 1/y。"""
    r = construction_p5_mod12(p)
    if r is None:
        return False, f"p={p} 不满足 p ≡ 5 (mod 12) 或非素数"
    _, x, y = r
    diff = sympy.Rational(4, p) - (
        sympy.Rational(1, p) + sympy.Rational(1, x) + sympy.Rational(1, y)
    )
    if sympy.simplify(diff) != 0:
        return False, f"p={p}: 验证失败 (x={x}, y={y})"
    return True, f"p={p}: (p, x, y) = ({p}, {x}, {y})"


def verify_all_p5_mod12(N: int) -> dict:
    """对 p ≤ N 的 p ≡ 5 (mod 12) 素数全验证。"""
    total = 0
    passed = 0
    failed = []
    for p in range(5, N + 1, 12):
        if not sympy.isprime(p):
            continue
        total += 1
        ok, reason = verify_p5_mod12(p)
        if ok:
            passed += 1
        else:
            failed.append((p, reason))
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{100 * passed // max(total, 1)}%",
    }