"""
test_example_learning.py

样例学习最小验证：连续 n 个正整数乘积被 n! 整除。

流程：
  1. 加载定理库
  2. 手动构造 4 条 HornClause（模拟 Qwen 输出）
  3. 加入 store
  4. 跑 prove(目标)
  5. 打印证明链 + 依赖记录

后续把"手动构造 4 条 HornClause"替换成"Qwen 输出 → HornClause"即可。
"""

import os
import glob

from numtheory_prover import (
    Prover, parse_goal, make_var, make_const, make_pred, HornClause
)
from adaptive_store import AdaptiveStore
from adaptive_prover import AdaptiveProver


# ============================================================
# 一、模拟 Qwen 输出的 4 条定理
# ============================================================
#
# 符号约定：
#   product_range(m, n) = m · (m+1) · ... · (m+n-1)
#   factorial(n)        = n!
#   binomial(N, k)      = C(N, k)
#   times(a, b)         = a · b
#   plus(a, b)          = a + b
#   minus(a, b)         = a - b
#   equals(a, b)        = a = b
#   integer(x)          = x 是整数
#   divides(a, b)       = a | b
#
# 人类证明的思路：
#   product_range(m, n) = n! · binomial(m+n-1, n)
#   且 binomial(m+n-1, n) 是整数
#   所以 n! | product_range(m, n)

def build_example_clauses():
    """构造 4 条 HornClause，模拟 Qwen 从人类文本解析出的结构化证明。"""
    clauses = []

    # --- 定理 1：组合数整性（公理，无 body） ---
    # integer(binomial(n, k))
    T_BINOM_INT = HornClause(
        id="T_BINOM_INT",
        name="组合数整性",
        head=make_pred("integer",
                       make_const("binomial", make_var("n"), make_var("k"))),
        body=[],
        category="组合数",
    )
    clauses.append(T_BINOM_INT)

    # --- 定理 2：连续整数乘积公式（公理，无 body） ---
    # equals(product_range(m, n),
    #        times(factorial(n), binomial(plus(m, minus(n, 1)), n)))
    T_PROD_RANGE_EQ = HornClause(
        id="T_PROD_RANGE_EQ",
        name="连续整数乘积公式",
        head=make_pred(
            "equals",
            make_const("product_range", make_var("m"), make_var("n")),
            make_const(
                "times",
                make_const("factorial", make_var("n")),
                make_const(
                    "binomial",
                    make_const("plus",
                               make_var("m"),
                               make_const("minus", make_var("n"), make_const("1"))),
                    make_var("n"),
                ),
            ),
        ),
        body=[],
        category="组合数",
    )
    clauses.append(T_PROD_RANGE_EQ)

    # --- 定理 3：整除定义（可选，如果系统需要） ---
    # 这里不加入，因为会引入 exists，先跳过。
    # divides(a, b) :- equals(b, times(a, c)), integer(c).   （用 exists c 表达）

    # --- 定理 4：结论（目标定理） ---
    # divides(factorial(n), product_range(m, n))
    #   :- equals(product_range(m, n),
    #             times(factorial(n), binomial(plus(m, minus(n, 1)), n))),
    #      integer(binomial(plus(m, minus(n, 1)), n)).
    T_CONCLUSION = HornClause(
        id="T_CONCLUSION",
        name="连续整数乘积能被 n! 整除",
        head=make_pred(
            "divides",
            make_const("factorial", make_var("n")),
            make_const("product_range", make_var("m"), make_var("n")),
        ),
        body=[
            make_pred(
                "equals",
                make_const("product_range", make_var("m"), make_var("n")),
                make_const(
                    "times",
                    make_const("factorial", make_var("n")),
                    make_const(
                        "binomial",
                        make_const("plus",
                                   make_var("m"),
                                   make_const("minus", make_var("n"), make_const("1"))),
                        make_var("n"),
                    ),
                ),
            ),
            make_pred(
                "integer",
                make_const(
                    "binomial",
                    make_const("plus",
                               make_var("m"),
                               make_const("minus", make_var("n"), make_const("1"))),
                    make_var("n"),
                ),
            ),
        ],
        category="组合数",
    )
    clauses.append(T_CONCLUSION)

    return clauses


# ============================================================
# 二、加载 store + 吸收样例
# ============================================================

def load_store():
    from numtheory_prover import build_theorem_db
    store = AdaptiveStore()
    for c in build_theorem_db():
        store.add(c)
    if os.path.exists('theorems.jsonl'):
        store.load_jsonl('theorems.jsonl')
    for p in sorted(glob.glob('theorems/*.jsonl')):
        store.load_jsonl(p)
    store.load_weights()
    store.load_dependency_records()
    return store


def absorb_example(store):
    """吸收样例：把 4 条新定理加入 store。"""
    clauses = build_example_clauses()
    added = 0
    for c in clauses:
        if c.id not in store.by_id:
            store.add(c)
            added += 1
            print(f"  [absorb] 加入定理: {c.id}  {c.name}")
    print(f"  [absorb] 共加入 {added} 条定理")
    return clauses


# ============================================================
# 三、主流程
# ============================================================

def main():
    print("=" * 70)
    print("样例学习：连续 n 个正整数乘积被 n! 整除")
    print("=" * 70)

    # 1. 加载 store
    print("\n[1] 加载定理库...")
    store = load_store()
    print(f"  初始定理数: {len(store.clauses)}")

    # 2. 吸收样例
    print("\n[2] 吸收样例（模拟 Qwen 输出）...")
    new_clauses = absorb_example(store)
    print(f"  吸收后定理数: {len(store.clauses)}")

    # 3. 构造目标
    print("\n[3] 构造目标...")
    goal_str = "divides(factorial(n), product_range(m, n))"
    goal = parse_goal(goal_str)
    print(f"  目标: {goal}")

    # 4. 跑证明
    print("\n[4] 开始证明...")
    ap = AdaptiveProver(store, max_rounds=3, base_top_k=20)
    proof = ap.prove(goal_str, strategy="direct", premises=[], verbose=True)

    # 5. 打印结果
    print("\n" + "=" * 70)
    print("结果")
    print("=" * 70)
    if proof:
        print(f"✓ 证明成功！证明链长度: {len(proof)}")
        print("\n证明链:")
        for i, step in enumerate(proof, 1):
            body_str = ", ".join(str(b) for b in step.clause.body)
            print(f"  [{i}] {step.clause.id}  {step.clause.name}")
            print(f"      head: {step.clause.head}")
            if body_str:
                print(f"      body: {body_str}")
    else:
        print("✗ 证明失败")

    # 6. 打印依赖记录
    print("\n依赖记录:")
    goal_key = (goal.name, len(goal.args))
    deps = store.dependency_records.get(goal_key, {})
    if deps:
        for dep_set, count in deps.items():
            print(f"  {goal_key} ← {tuple(sorted(dep_set))}  (count={count})")
    else:
        print(f"  (无 {goal_key} 的依赖记录)")

    # 7. 保存
    store.save_weights()
    store.save_dependency_records()
    print("\n权重和依赖记录已保存")


if __name__ == "__main__":
    main()