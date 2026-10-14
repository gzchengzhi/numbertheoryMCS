"""
诊断：为什么样例学习证明失败
"""
import os
import glob
from numtheory_prover import (
    Prover, parse_goal, make_var, make_const, make_pred, HornClause
)
from adaptive_store import AdaptiveStore
from test_example_learning import build_example_clauses, load_store


def main():
    print("=" * 70)
    print("诊断样例学习失败原因")
    print("=" * 70)

    store = load_store()
    print(f"初始定理数: {len(store.clauses)}")

    # 吸收样例
    for c in build_example_clauses():
        if c.id not in store.by_id:
            store.add(c)
    print(f"吸收后定理数: {len(store.clauses)}")

    goal = parse_goal("divides(factorial(n), product_range(m, n))")
    print(f"\n目标: {goal}")

    # 1. 看 _score_all
    print("\n[1] _score_all 原始分数（前 10）:")
    scores = store._score_all(goal)
    for cid, sc in sorted(scores.items(), key=lambda x: -x[1])[:10]:
        print(f"    {cid}: {sc:.2f}")

    # 2. 看 retrieve_adaptive 返回
    print("\n[2] retrieve_adaptive 返回（top_k=10）:")
    candidates = store.retrieve_adaptive(goal, top_k=10)
    for i, c in enumerate(candidates):
        print(f"    {i}. {c.id}  {c.head}")

    # 3. 手动试 T_CONCLUSION
    print("\n[3] 手动展开 T_CONCLUSION:")
    if "T_CONCLUSION" not in store.by_id:
        print("    T_CONCLUSION 不在 by_id！")
        return
    tc = store.by_id["T_CONCLUSION"]
    print(f"    head: {tc.head}")
    print(f"    body[0]: {tc.body[0]}")
    print(f"    body[1]: {tc.body[1]}")

    # 4. 手动检查 T_CONCLUSION 的 body[0] 与 T_PROD_RANGE_EQ 的 head 能否 unify
    print("\n[4] 检查 body[0] 与 T_PROD_RANGE_EQ 的 unify:")
    from numtheory_prover import unify
    prover = Prover(store, max_depth=12)
    renamed_tc = prover._rename_clause(tc, 0)
    print(f"    renamed T_CONCLUSION head: {renamed_tc.head}")
    print(f"    renamed T_CONCLUSION body[0]: {renamed_tc.body[0]}")
    print(f"    renamed T_CONCLUSION body[1]: {renamed_tc.body[1]}")

    # T_PROD_RANGE_EQ 的 head
    tre = store.by_id["T_PROD_RANGE_EQ"]
    renamed_tre = prover._rename_clause(tre, 0)
    print(f"    renamed T_PROD_RANGE_EQ head: {renamed_tre.head}")

    # 手动 unify
    sub = unify(renamed_tc.head, goal, {})
    print(f"\n    步骤 1: unify(T_CONCLUSION.head, goal) = {sub}")
    if sub:
        body0_sub = prover._substitute_if_has(renamed_tc.body[0], sub) if hasattr(prover, '_substitute_if_has') else renamed_tc.body[0]
        from numtheory_prover import substitute
        body0_sub = substitute(renamed_tc.body[0], sub)
        body1_sub = substitute(renamed_tc.body[1], sub)
        print(f"    步骤 2: body[0] 替换后 = {body0_sub}")
        print(f"    步骤 2: body[1] 替换后 = {body1_sub}")

        # unify body[0] 和 T_PROD_RANGE_EQ.head
        sub2 = unify(body0_sub, renamed_tre.head, {})
        print(f"    步骤 3: unify(body[0], T_PROD_RANGE_EQ.head) = {sub2}")

    # 5. 用 max_depth 检查
    print("\n[5] 直接调用 _prove_recursive 并计数:")
    prover.step_count = 0
    prover.max_steps = 100
    result = prover._prove_recursive(goal, {}, 0, [], strategy="direct")
    print(f"    step_count = {prover.step_count}")
    print(f"    result = {'SUCCESS' if result else 'FAIL'}")


if __name__ == "__main__":
    main()