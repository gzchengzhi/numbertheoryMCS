"""
一步到位：吸收样例 → 标记 → 证明

用法：
  python test_learn_and_prove.py

前两步（absorb_example.py / test_example_learning.py）合并成一个进程，
使得 store._learned_ids 在证明时有效。
"""

import os
import glob

from numtheory_prover import parse_goal, HornClause
from adaptive_store import AdaptiveStore
from adaptive_prover import AdaptiveProver


# ── 1. 加载 store ──────────────────────────────────
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


# ── 2. 5 条样例定理 ─────────────────────────────────
def build_example_clauses():
    clauses = []

    clauses.append(HornClause(
        id="T_BINOM_INT", name="组合数整性",
        head=parse_goal("integer(binomial(n, k))"),
        body=[], category="组合数",
    ))

    clauses.append(HornClause(
        id="T_PROD_RANGE_EQ", name="连续整数乘积公式",
        head=parse_goal(
            "equals(product_range(m, n), "
            "times(factorial(n), binomial(plus(m, minus(n, 1)), n)))"
        ),
        body=[], category="组合数",
    ))

    clauses.append(HornClause(
        id="T_MUL_DIVIDES", name="整数乘积整除性",
        head=parse_goal("divides(a, times(a, c))"),
        body=[parse_goal("integer(a)"), parse_goal("integer(c)")],
        category="基础",
    ))

    clauses.append(HornClause(
        id="T_FACT_INT", name="阶乘整性",
        head=parse_goal("integer(factorial(n))"),
        body=[], category="基础",
    ))

    clauses.append(HornClause(
        id="T_EQUAL_SUBST", name="等量代换",
        head=parse_goal("divides(a, c)"),
        body=[
            parse_goal("equals(c, times(a, d))"),
            parse_goal("divides(a, times(a, d))"),
        ],
        category="基础",
    ))

    return clauses


# ── 3. 主流程 ──────────────────────────────────
def main():
    print("=" * 70)
    print("样例学习 → 标记 → 证明")
    print("=" * 70)

    print("\n[1] 加载定理库...")
    store = load_store()
    print(f"  初始定理数: {len(store.clauses)}")

    print("\n[2] 吸收 + 标记...")
    new_ids = []
    for c in build_example_clauses():
        if c.id not in store.by_id:
            store.add(c)
            print(f"  [absorb] 加入: {c.id}  {c.name}")
        else:
            print(f"  [absorb] 已存在: {c.id}")
        new_ids.append(c.id)

    store.mark_learned(new_ids)
    print(f"  → 标记了 {len(new_ids)} 条定理")
    print(f"  → 吸收后定理数: {len(store.clauses)}")

    print("\n[3] 构造目标...")
    goal_str = "divides(factorial(n), product_range(m, n))"
    goal = parse_goal(goal_str)
    print(f"  目标: {goal}")

    print("\n[4] 开始证明...")
    ap = AdaptiveProver(store)
    proof = ap.prove(goal_str, strategy="direct", premises=[], verbose=True)

    print("\n" + "=" * 70)
    print("结果")
    print("=" * 70)
    if proof:
        print(f"[OK] 证明成功！链长 {len(proof)}")
        for i, step in enumerate(proof, 1):
            print(f"  {i}. {step.clause.id}  {step.clause.name}")
            print(f"      head: {step.clause.head}")
            if step.clause.body:
                for j, b in enumerate(step.clause.body):
                    print(f"      body[{j}]: {b}")
    else:
        print("[X] 证明失败")

    # 依赖记录
    print("\n依赖记录:")
    goal_key = (goal.name, len(goal.args))
    deps = store.dependency_records.get(goal_key, {})
    if deps:
        for dep_set, count in deps.items():
            print(f"  {goal_key} ← {tuple(sorted(dep_set))}  (count={count})")
    else:
        print(f"  (无 {goal_key} 的依赖记录)")

    # 保存
    store.save_weights()
    store.save_dependency_records()
    print("\n权重和依赖记录已保存")


if __name__ == "__main__":
    main()