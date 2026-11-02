#!/usr/bin/env python3
"""
加载 12_0_competition 定理库，报告：
  - 总定理数
  - 新加的 COMP-* 条数
  - 结构去重后实际进 clauses 的条数
  - 每条 COMP-* 是否被 alias（结构重复）
  - 新定理能匹配到 concept_neurons 的条数
"""
import sys, os, glob, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from adaptive_store import AdaptiveStore
from numtheory_prover import parse_goal
from concept_triangle import extract_triangles
from sympy_bridge import to_sympy


def main():
    store = AdaptiveStore()
    # ★ 新增：加载神经元（之前漏了）
    store.load_neurons("theorems/concept_neurons.json")   # ← 路径按你实际改
    print(f"[load] 神经元: {len(store.concept_neurons)} 个")

    # 1. 加载原有文件
    base_files = sorted(glob.glob("theorems/*.jsonl"))
    for f in base_files:
        store.load_jsonl(f)
    print(f"[load] 原有 clauses = {len(store.clauses)}")   # ★ 注意这里实际是翻倍的，先不管

    # 2. 加载 COMP
    # 新
    comp_file = os.path.join(ROOT, "theorems", "12_0_competition.jsonl")
    if os.path.exists(comp_file):
        store.load_jsonl(comp_file)

    # ★ 3. 用 set 统计 COMP-* 唯一 id
    comp_ids = sorted({c.id for c in store.clauses if c.id.startswith("COMP-")})
    print(f"[stat] COMP-* 唯一 id: {len(comp_ids)} / 70")

    # ★ 4. 对每个唯一 id 只跑一次 extract_triangles
    by_id = {c.id: c for c in store.clauses if c.id.startswith("COMP-")}
    hit, miss = 0, []
    for cid in comp_ids:
        c = by_id[cid]
        try:
            r = extract_triangles(c, to_sympy, store)
        except Exception as e:
            miss.append((cid, f"异常: {e!r}"))
            continue
        n = len(r.get("triangles", []))
        if n > 0:
            hit += 1
        else:
            miss.append((cid, "0 三角形"))

    print(f"\n[triangle] 真实覆盖率: {hit}/{len(comp_ids)}")
    if miss:
        print("[triangle] 未命中列表:")
        for cid, reason in miss:
            print(f"  {cid}: {reason}")


if __name__ == "__main__":
    main()