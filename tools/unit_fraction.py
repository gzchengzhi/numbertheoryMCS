# tools/unit_fraction.py
"""19.0.1 单位分数证明（外围 sympy 验证，不碰内部 _verify_construct）。

对应 Cheng 2019 §8.5.3 注意力控制：
  - 失败时枚举 (2,3,6)，聚焦"缺什么神经元"
  - 成功时 solidify 写回新神经元

纪律：
  - 不 import deep_recursive_prover / recursive_prover / adaptive_store 的私有方法
  - 只用 sympy + numtheory_prover 的公开 parse_goal
"""
import sympy
from typing import Optional, Tuple

# ============================================================
# 1. 枚举埃及分数三项：1/a + 1/b + 1/c == 1
# ============================================================
def find_egyptian_3_terms(max_c: int = 20) -> Optional[Tuple[int, int, int]]:
    """枚举 a<=b<=c，1/a+1/b+1/c == 1，返回第一个解 (2,3,6)。

    (2,3,6) 是最小解：1/2+1/3+1/6 = 3/6+2/6+1/6 = 1。
    """
    for a in range(2, max_c + 1):
        for b in range(a, max_c + 1):
            for c in range(b, max_c + 1):
                if (sympy.Rational(1, a)
                        + sympy.Rational(1, b)
                        + sympy.Rational(1, c)) == 1:
                    return (a, b, c)
    return None


# ============================================================
# 2. 缩放等式：1/n - (1/(an) + 1/(bn) + 1/(cn))
# ============================================================
def scale_equation(n, a: int, b: int, c: int):
    """返回 1/n - (1/(an)+1/(bn)+1/(cn)) 的 sympy 化简结果（应为 0）。

    n 可以是 int（具体题）或 sympy.Symbol（符号题）。
    """
    if hasattr(n, "free_symbols"):
        ns = n
    else:
        ns = sympy.Symbol(str(n), integer=True, positive=True)
    return sympy.cancel(1 / ns - (1 / (a * ns) + 1 / (b * ns) + 1 / (c * ns)))


# ============================================================
# 3. 从 goal 提取 n
# ============================================================
def extract_n(goal_str: str):
    """从 'unit_fraction_sum(x,y,z,n)' 或 'unit_fraction_sum(x,y,z,5)' 提 n。

    返回 int 或 sympy.Symbol；无法解析返回 None。
    """
    from numtheory_prover import parse_goal, Var, Const
    goal = parse_goal(goal_str)
    if goal is None or goal.name != "unit_fraction_sum" or len(goal.args) != 4:
        return None
    n_arg = goal.args[3]
    if isinstance(n_arg, Const) and n_arg.name.lstrip("-").isdigit():
        return int(n_arg.name)
    if isinstance(n_arg, Var):
        return sympy.Symbol(n_arg.name, integer=True, positive=True)
    return None


# ============================================================
# 4. 外围验证（选项 A：不依赖 proof.substitution）
# ============================================================
def verify_unit_fraction(goal_str: str, proof=None) -> Tuple[bool, str]:
    """外围验证：从 goal 取 n，枚举 (2,3,6)，sympy.cancel 验证。

    选项 A：proof 里 x/y/z 可能是 Var（_apply_construct 不填），
    所以不依赖 proof.substitution，自己从 goal 提 n、自己算构造。
    """
    n = extract_n(goal_str)
    if n is None:
        return False, f"无法从 goal 提取 n: {goal_str}"
    terms = find_egyptian_3_terms()
    if terms is None:
        return False, "枚举 (2,3,6) 失败"
    a, b, c = terms
    diff = scale_equation(n, a, b, c)
    if sympy.simplify(diff) != 0:
        return False, f"sympy 验证失败: a={a},b={b},c={c}, diff={diff}"
    return True, f"x={a}*n, y={b}*n, z={c}*n, sympy.cancel=0"


# ============================================================
# 5. solidify 写回（首次枚举成功后，缓存为图式层神经元）
# ============================================================
def solidify_unit_fraction(
        store,
        nid: str = "NEURON::S::unit_fraction_sum<-gt::arity=1",
) -> Optional[str]:
    """首次枚举成功后，把 (2,3,6) 写回神经元（缓存态）。

    写回后 head_pattern 带 times(2,n)/times(3,n)/times(6,n)，
    下次 prove_deep 图式层直接命中，proof.substitution 有 x→times(2,n)。

    注意：
      - AdaptiveStore.add_triangle 对已存在 nid 不覆盖（防重复），先 del 再 add。
      - lower 只留 gt(n,0)，不放 egyptian_3_terms——
        _match_lower 对普通 list 走 premises 匹配，不放 premises 会失败。
        egyptian_3_terms 独立成神经元，不挂 unit_fraction_sum 的 lower。
    """
    terms = find_egyptian_3_terms()
    if terms is None:
        return None
    a, b, c = terms
    triangle = {
        "neuron": nid,
        "type": "single",
        "lower": [["gt", ["n", "0"]]],   # ★ 去掉 egyptian_3_terms
        "mediator": None,
        "anchor": None,
        "head_pattern": [
            "unit_fraction_sum",
            [f"times({a},n)", f"times({b},n)", f"times({c},n)", "n"],
        ],
        "N": 1,
        "weight": 1.0,
    }
    if nid in store.concept_neurons:
        del store.concept_neurons[nid]
    store.add_triangle(triangle, "UNIT_FRACTION_ENUM")
    return nid