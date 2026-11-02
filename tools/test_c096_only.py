# -*- coding: utf-8 -*-
"""
Created on Mon Nov  2 08:13:33 2026

@author: gzche
"""

# tools/test_c096_only.py
"""C096 独立证明：只加载 C096 的神经元 + 定理，不走主库 120 题。"""
import sys, os, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from adaptive_store import AdaptiveStore
from recursive_prover import RecursiveProver

import numtheory_prover
numtheory_prover.ENABLE_SUBST_CONSISTENCY = True
numtheory_prover.ENABLE_EMPTY_LOWER = True


def main():
    # 1. 全新的 store
    store = AdaptiveStore()

    # 2. 只加载 C096 的定理（theorems/c096_pythagorean.jsonl）
    if os.path.exists("theorems/c096_pythagorean.jsonl"):
        store.load_jsonl("theorems/c096_pythagorean.jsonl")
        print(f"[load] c096_pythagorean.jsonl: {len(store.clauses)} clauses")
    else:
        print("[warn] theorems/c096_pythagorean.jsonl 不存在")

    # 3. 只加载 C096 的神经元（theorems/c096_pythagorean_neurons.json）
    with open("theorems/c096_pythagorean_neurons.json", encoding="utf-8") as f:
        c096_data = json.load(f)
    store.concept_neurons = c096_data["concept_neurons"]
    store._neurons_built = True
    if hasattr(store, "_head_index"):
        del store._head_index
    if hasattr(store, "_clause_head_index"):
        del store._clause_head_index
    print(f"[load] c096 神经元: {len(store.concept_neurons)}")

    # 4. 构造 RecursiveProver，verbose=True
    rp = RecursiveProver(store, iso_edges_path="data/iso_edges.json", verbose=True)

    # 5. 只测 C096
    goal = "exists(m, exists(n, and(gt(m,n), coprime(m,n), equals(a, minus(power(m,2),power(n,2))), equals(b, times(2,times(m,n))), equals(c, plus(power(m,2),power(n,2))))))"
    premises = [
        "equals(plus(power(a,2),power(b,2)), power(c,2))",
        "gt(a,0)", "gt(b,0)", "gt(c,0)",
    ]
    print(f"\n[test] goal = {goal}")
    print(f"[test] premises = {premises}")
    proof = rp.prove(goal, premises=premises, verbose=True)

    print(f"\n=== RESULT ===")
    if proof:
        for s in proof:
            print(f"  strategy={s.strategy}")
            print(f"  subgoal={s.subgoal}")
            print(f"  substitution={s.substitution}")
    else:
        print("  未证明")


if __name__ == "__main__":
    main()