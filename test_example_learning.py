"""
test_example_learning.py

样例学习验证（证明阶段）：连续 n 个正整数乘积被 n! 整除。

前置：先跑 python absorb_example.py

跑法：
  python test_example_learning.py
"""

import os
import glob

from numtheory_prover import Prover, parse_goal, HornClause
from adaptive_store import AdaptiveStore
from adaptive_prover import AdaptiveProver


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


def main():
    print("=" * 70)
    print("样例学习验证：连续 n 个正整数乘积被 n! 整除")
    print("=" * 70)

    # 1. 加载 store
    print("\n[1] 加载定理库...")
    store = load_store()
    print(f"  定理数: {len(store.clauses)}")

    # 2. 检查 5 条定理是否在库
    print("\n[2] 检查吸收的定理...")
    for tid in ["T_BINOM_INT", "T_PROD_RANGE_EQ",
                "T_MUL_DIVIDES", "T_FACT_INT", "T_EQUAL_SUBST"]:
        if tid in store.by_id:
            print(f"  [OK] {tid} 在库")
        else:
            print(f"  [X] {tid} 不在库——请先跑 absorb_example.py")
            return

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
        print(f"[OK] 证明成功！证明链长度: {len(proof)}")
        print("\n证明链:")
        for i, step in enumerate(proof, 1):
            print(f"  [{i}] {step.clause.id}  {step.clause.name}")
            print(f"      head: {step.clause.head}")
            if step.clause.body:
                print(f"      body: {[str(b) for b in step.clause.body]}")
    else:
        print("[X] 证明失败")

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