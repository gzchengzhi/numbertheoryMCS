# tools/erdos_straus_mod4.py
"""19.0.3 p ≡ 3 (mod 4) 的 Erdős–Straus 证明：候选生成 + 筛选 + 学习。

流程（系统自主，不手写构造）：
  阶段 1：概念三角形 A/A'/B（theorems/19_0_p3_mod4.json）——通用规则
  阶段 2：generate_candidates(p) 生成候选 a = (p + 4k + 1)/4
          filter_candidates(p, cands) 筛选 4/p - 1/a = 1/m（m 正整数）
  阶段 3：try_candidate(p, a) 验证 4/p = 1/a + 1/b + 1/c（b=m+1, c=m(m+1)）
          solidify_candidate(store, p, a) 成功候选写回神经元（学习）

关键公式（已确认）：
  4/p - 1/a = 1/m，m 正整数。
  a = (p+1)/4 时：1/a = 4/(p+1)，4/p - 4/(p+1) = 4/(p(p+1)) = 1/m，m = p(p+1)/4。
  a = (p-3)/4 时：1/a = 4/(p-3)，4/p - 4/(p-3) = -12/(p(p-3)) < 0，排除。

纪律：
  - 不 import deep_recursive_prover / recursive_prover / adaptive_store 的私有方法
  - 只用 sympy + numtheory_prover 的公开 parse_goal
"""
import sympy
from typing import List, Tuple, Optional


# ============================================================
# 阶段 2：候选生成
# ============================================================
def generate_candidates(p: int, n_candidates: int = 5) -> List[int]:
    """生成候选 a = (p + 4k + 1) / 4，k = 0, -1, 1, -2, 2, ...

    对 p ≡ 3 (mod 4)，p + 4k + 1 ≡ 0 (mod 4)，所以 (p+4k+1)/4 是整数。
    按 |k| 递增，k=0 最优先（(p+1)/4）。
    """
    if p % 4 != 3:
        return []
    cands = []
    ks = [0, -1, 1, -2, 2, -3, 3, -4, 4, -5, 5]
    for k in ks[:n_candidates]:
        num = p + 4 * k + 1
        if num > 0 and num % 4 == 0:
            a = num // 4
            if a > 0:
                cands.append(a)
    return cands


# ============================================================
# 阶段 2：候选筛选（4/p - 1/a = 1/m，m 正整数）
# ============================================================
def filter_candidates(p: int, cands: List[int]) -> List[Tuple[int, int]]:
    """筛选：4/p - 1/a 必须是正单位分数 1/m（m 正整数）。

    返回 [(a, m)]。
    """
    result = []
    for a in cands:
        if a <= 0:
            continue
        diff = sympy.Rational(4, p) - sympy.Rational(1, a)
        if diff <= 0:
            continue  # 必须是正单位分数
        # diff = 1/m → m = 1/diff
        m = sympy.Rational(1, 1) / diff
        if not m.is_integer or m <= 0:
            continue
        result.append((a, int(m)))
    return result


# ============================================================
# 阶段 3：验证单个候选
# ============================================================
def try_candidate(p: int, a: int) -> Tuple[bool, Optional[Tuple[int, int, int]]]:
    """验证 a 是否可行：4/p = 1/a + 1/b + 1/c，b=m+1, c=m(m+1)。

    返回 (ok, (a,b,c))。
    """
    if a <= 0:
        return False, None
    diff = sympy.Rational(4, p) - sympy.Rational(1, a)
    if diff <= 0:
        return False, None
    m = sympy.Rational(1, 1) / diff
    if not m.is_integer or m <= 0:
        return False, None
    m_int = int(m)
    b = m_int + 1
    c = m_int * (m_int + 1)
    # 最终验证：1/a + 1/b + 1/c == 4/p
    lhs = (sympy.Rational(1, a)
           + sympy.Rational(1, b)
           + sympy.Rational(1, c))
    if sympy.simplify(sympy.Rational(4, p) - lhs) != 0:
        return False, None
    return True, (a, b, c)


# ============================================================
# 阶段 3：学习（成功候选写回神经元）
# ============================================================
def solidify_candidate(store, p: int, a: int) -> Optional[str]:
    """成功候选写回神经元，下次 prove_deep 直接命中。

    a = (p + 4k + 1)/4，k 从 a 反推：k = (4a - p - 1)/4。
    head_pattern 里 a 用表达式 div(plus(p, 4k+1), 4)，p 是 Var。
    """
    ok, abc = try_candidate(p, a)
    if not ok:
        return None
    k = (4 * a - p - 1) // 4
    offset = 4 * k + 1
    if offset >= 0:
        a_expr = f"div(plus(p,{offset}),4)" if offset != 0 else "div(p,4)"
    else:
        a_expr = f"div(minus(p,{-offset}),4)"
    # nid 用 a_expr 的简化形式
    safe = a_expr.replace("(", "_").replace(")", "").replace(",", "_")
    nid = f"NEURON::S::unit_fraction_p3::{safe}"
    if nid in store.concept_neurons:
        return nid
    triangle = {
        "neuron": nid,
        "type": "single",
        "lower": [
            ["congruent", ["p", "3", "4"]],
            ["integer", [a_expr]],
        ],
        "mediator": None,
        "anchor": None,
        "head_pattern": [
            "unit_fraction_sum",
            [a_expr, "plus(m,1)", "times(m,plus(m,1))", "p"],
        ],
        "N": 1,
        "weight": 1.0,
    }
    store.add_triangle(triangle, "P3_MOD4_SOLIDIFY")
    return nid


# ============================================================
# 阶段 2+3 完整：对 p ≡ 3 (mod 4) 找到最优候选
# ============================================================
def find_optimal_candidate(p: int, n_candidates: int = 5) -> Optional[Tuple[int, int, int]]:
    """生成候选 → 筛选 → 验证，返回第一个成功的 (a,b,c)。"""
    if p % 4 != 3:
        return None
    cands = generate_candidates(p, n_candidates)
    filtered = filter_candidates(p, cands)
    for (a, _m) in filtered:
        ok, abc = try_candidate(p, a)
        if ok:
            return abc
    return None


# ============================================================
# 全范围验证
# ============================================================
def verify_all_p3_mod4(N: int) -> dict:
    """对 p ≤ N 的 p ≡ 3 (mod 4) 素数，全验证。"""
    from sympy import isprime
    total = 0
    passed = 0
    failed = []
    for p in range(3, N + 1, 4):
        if not isprime(p):
            continue
        total += 1
        abc = find_optimal_candidate(p)
        if abc is None:
            failed.append(p)
        else:
            passed += 1
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{100*passed//max(total,1)}%",
    }