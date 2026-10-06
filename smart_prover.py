# -*- coding: utf-8 -*-
"""
Created on Tue Oct  6 11:15:27 2026

@author: gzche
"""

"""
智能证明器：先检索，再证明。
"""

from typing import List, Optional
from numtheory_prover import Prover, parse_goal, Var, ProofStep
from theorem_store import TheoremStore


class SmartProver:
    def __init__(self, store: TheoremStore, top_k: int = 20):
        self.store = store
        self.top_k = top_k

    def prove(self, goal_str: str, strategy: str = "auto",
              var: Optional[Var] = None,
              verbose: bool = True) -> Optional[List[ProofStep]]:
        goal = parse_goal(goal_str)
        if goal is None:
            return None

        # 1. 检索相关定理
        if verbose:
            print(f"\n[1] 检索相关定理（top-{self.top_k}）...")
        relevant = self.store.retrieve(goal, top_k=self.top_k)
        if verbose:
            print(f"    命中 {len(relevant)} 条:")
            for c in relevant[:5]:
                print(f"      {c.id} {c.name}")
            if len(relevant) > 5:
                print(f"      ... 还有 {len(relevant)-5} 条")

        # 2. 只用相关定理构造 Prover
        prover = Prover(relevant, max_depth=12)

        # 3. 证明
        if verbose:
            print(f"\n[2] 开始证明（策略: {strategy}）...")
        proof = prover.prove(goal, strategy=strategy, var=var, verbose=False)

        return proof


# ---------- CLI ----------
def cli():
    import argparse
    parser = argparse.ArgumentParser(description="智能定理证明器")
    parser.add_argument('--data', type=str, default='theorems.jsonl')
    parser.add_argument('--prove', type=str, required=True)
    parser.add_argument('--strategy', choices=['auto', 'direct', 'contradiction', 'induction'],
                        default='auto')
    parser.add_argument('--var', type=str, default=None)
    parser.add_argument('--top_k', type=int, default=20)
    parser.add_argument('--stats', action='store_true')
    args = parser.parse_args()

    store = TheoremStore()
    store.load_jsonl(args.data)

    if args.stats:
        print(store.stats())
        return

    sp = SmartProver(store, top_k=args.top_k)
    var = Var(args.var) if args.var else None
    proof = sp.prove(args.prove, strategy=args.strategy, var=var, verbose=True)

    # 输出
    from numtheory_prover import print_proof
    print_proof(proof, parse_goal(args.prove))


if __name__ == "__main__":
    cli()