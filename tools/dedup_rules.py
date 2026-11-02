"""
去重规则表。独立于 dedup_theorems.py，方便扩充。
L3 语义等价规则：把 (pattern, canonical) 对登记在这里。
注意：这里的规则只用于"归类"，不用于"删除"。
"""

# L3 语义等价对：src 与 dst 被视为同一语义组
SEMANTIC_EQUIV = [
    # 同余 ⟺ 整除差
    {
        "left":  ("congruent", ["a", "b", "m"]),
        "right": ("divides",   ["m", "minus(a,b)"]),
        "guard": ["gt(m, 0)"],
        "group": "congruence_divide",
    },
    # gcd = 1 ⟺ coprime
    {
        "left":  ("equals",  ["gcd(a,b)", "1"]),
        "right": ("coprime", ["a", "b"]),
        "guard": [],
        "group": "coprime_gcd1",
    },
    # lt 与 gt 对偶
    {
        "left":  ("lt", ["a", "b"]),
        "right": ("gt", ["b", "a"]),
        "guard": [],
        "group": "order_dual",
    },
    # le 与 ge 对偶
    {
        "left":  ("le", ["a", "b"]),
        "right": ("ge", ["b", "a"]),
        "guard": [],
        "group": "order_dual_le_ge",
    },
    # not_divides ⟺ divides 的否定
    {
        "left":  ("not_divides", ["a", "b"]),
        "right": ("not", ["divides(a,b)"]),
        "guard": [],
        "group": "not_divides_neg",
    },
    # prime 定义：gt(1) ∧ no_proper_divisor
    {
        "left":  ("prime", ["p"]),
        "right": ("and", ["gt(p,1)", "no_proper_divisor(p)"]),
        "guard": [],
        "group": "prime_definition",
    },
]

# 同一谓词的"可交换参数"位置（如 congruent 的 a/b 对称）
COMMUTATIVE_ARGS = {
    "congruent": [(0, 1)],   # a≡b 等价于 b≡a
    "equals":    [(0, 1)],
    "coprime":   [(0, 1)],
    "divides":   [],         # 非交换
    "lt":        [],
    "gt":        [],
}