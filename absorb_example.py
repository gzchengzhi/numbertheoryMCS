"""
absorb_example.py

吸收样例：把人类已证的定理加入定理库，持久化到文件。

用法：
  python absorb_example.py

跑完后：
  - theorems/learned.jsonl 会被写入（或追加）
  - theorem_weights.json / dependency_records.json 更新

然后跑：
  python test_example_learning.py
"""

import os
import json

from numtheory_prover import parse_goal, HornClause
from adaptive_store import AdaptiveStore


def build_example_clauses():
    """从人类证明解析出的结构化 HornClause"""
    clauses = []

    # 定理 1：组合数整性
    T_BINOM_INT = HornClause(
        id="T_BINOM_INT",
        name="组合数整性",
        head=parse_goal("integer(binomial(n, k))"),
        body=[],
        category="组合数",
    )
    clauses.append(T_BINOM_INT)

    # 定理 2：连续整数乘积公式
    T_PROD_RANGE_EQ = HornClause(
        id="T_PROD_RANGE_EQ",
        name="连续整数乘积公式",
        head=parse_goal(
            "equals(product_range(m, n), "
            "times(factorial(n), binomial(plus(m, minus(n, 1)), n)))"
        ),
        body=[],
        category="组合数",
    )
    clauses.append(T_PROD_RANGE_EQ)

    # ★ 定理 3：乘积整除性（数学上"显然"，但系统需要显式）
    # divides(a, times(a, c)) :- integer(a), integer(c)
    T_MUL_DIVIDES = HornClause(
        id="T_MUL_DIVIDES",
        name="整数乘积整除性",
        head=parse_goal("divides(a, times(a, c))"),
        body=[
            parse_goal("integer(a)"),
            parse_goal("integer(c)"),
        ],
        category="基础",
    )
    clauses.append(T_MUL_DIVIDES)

    # ★ 定理 4：阶乘整性
    T_FACT_INT = HornClause(
        id="T_FACT_INT",
        name="阶乘整性",
        head=parse_goal("integer(factorial(n))"),
        body=[],
        category="基础",
    )
    clauses.append(T_FACT_INT)

    # ★ 定理 5：等量代换
    # divides(a, c) :- equals(c, times(a, d)), divides(a, times(a, d))
    T_EQUAL_SUBST = HornClause(
        id="T_EQUAL_SUBST",
        name="等量代换",
        head=parse_goal("divides(a, c)"),
        body=[
            parse_goal("equals(c, times(a, d))"),
            parse_goal("divides(a, times(a, d))"),
        ],
        category="基础",
    )
    clauses.append(T_EQUAL_SUBST)

    return clauses


def load_store():
    from numtheory_prover import build_theorem_db
    import glob

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


def absorb():
    print("=" * 70)
    print("吸收样例：连续 n 个正整数乘积被 n! 整除")
    print("=" * 70)

    print("\n[1] 加载定理库...")
    store = load_store()
    print(f"  初始定理数: {len(store.clauses)}")

    print("\n[2] 吸收新定理...")
    clauses = build_example_clauses()
    added = 0
    skipped = 0
    for c in clauses:
        if c.id not in store.by_id:
            store.add(c)
            added += 1
            print(f"  [absorb] 加入: {c.id}  {c.name}")
        else:
            skipped += 1
            print(f"  [absorb] 已存在，跳过: {c.id}")
    print(f"  → 加入 {added} 条，跳过 {skipped} 条")
    print(f"  → 吸收后定理数: {len(store.clauses)}")

    # 持久化到 learned.jsonl
    print("\n[3] 写入 theorems/learned.jsonl...")
    os.makedirs("theorems", exist_ok=True)
    learned_file = os.path.join("theorems", "learned.jsonl")

    # 读已有内容，避免重复
    existing_ids = set()
    if os.path.exists(learned_file):
        with open(learned_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    existing_ids.add(rec.get("id"))
                except json.JSONDecodeError:
                    pass

    written = 0
    with open(learned_file, 'a', encoding='utf-8') as f:
        for c in clauses:
            if c.id in existing_ids:
                continue
            record = {
                "id": c.id,
                "name": c.name,
                "category": c.category,
                "head": str(c.head),
                "body": [str(b) for b in c.body],
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1
    print(f"  → 写入 {written} 条到 {learned_file}")

    # 保存权重
    store.save_weights()
    store.save_dependency_records()
    print("\n[4] 权重和依赖记录已保存")
    print("\n完成。下一步跑：python test_example_learning.py")


if __name__ == "__main__":
    absorb()