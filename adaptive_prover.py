"""
自适应证明器：一次检索 + 一次学习 + 概念多边形建边 + 链式建边 + 独立依赖记录
"""
import os
import argparse
from typing import List, Optional

from numtheory_prover import (
    Prover, parse_goal, Var, ProofStep, print_proof, HornClause
)
from adaptive_store import AdaptiveStore


class AdaptiveProver:
    def __init__(self, store: AdaptiveStore, max_rounds: int = 1,
                 base_top_k: Optional[int] = None):
        self.store = store
        self.max_rounds = max_rounds       # ★ 默认 1，只跑一轮
        self.base_top_k = base_top_k        # ★ 默认 None，返回全部

    def _register_premises(self, premises: List[str]) -> List[HornClause]:
        result = []
        for i, p in enumerate(premises or []):
            pg = parse_goal(p)
            if pg is None:
                continue
            c = HornClause(f"PREM_{i}", f"前提 {p}", pg, [], category="前提")
            if c.id not in self.store.by_id:
                self.store.add(c)
            result.append(c)
        return result

    def _cleanup_premises(self, prem_clauses: List[HornClause]):
        for c in prem_clauses:
            if c.id in self.store.by_id:
                del self.store.by_id[c.id]
                try:
                    self.store.clauses.remove(c)
                except ValueError:
                    pass
                if hasattr(self.store, 'by_predicate'):
                    try:
                        self.store.by_predicate[c.head.name].remove(c.id)
                    except (KeyError, ValueError):
                        pass

    def prove(self, goal_str: str, strategy: str = "auto",
              var: Optional[Var] = None,
              premises: Optional[List[str]] = None,
              verbose: bool = True) -> Optional[List[ProofStep]]:
        goal = parse_goal(goal_str)
        if goal is None:
            if verbose:
                print(f"无法解析: {goal_str}")
            return None

        try:
            from symbolic import simplify_predicate
            _s = simplify_predicate(goal)
            if _s != goal:
                goal = _s
        except Exception:
            pass

        # ★ 快速通道：无 premises 时，先试底层 Prover
        if not premises:
            prover = Prover(self.store, max_depth=12)
            proof = prover.prove(goal, strategy=strategy, var=var, verbose=False)
            if proof is not None:
                if verbose:
                    print(f"[fast] 快速通道成功")
                # 记录依赖 + 强化
                used_ids = [s.clause.id for s in proof]
                self.store.strengthen(used_ids)
                self.store.learn_cooccurrence(used_ids)
                self.store.record_dependency(goal, [s.clause for s in proof])
                return proof


        prem_clauses = self._register_premises(premises or [])

        # ★ 学习阶段：建边（一次）
        if prem_clauses:
            try:
                n_found = self.store.discover_polygons(goal, prem_clauses)
                if verbose and n_found > 0:
                    print(f"[concept] 发现 {n_found} 个概念多边形")
            except Exception as e:
                if verbose:
                    print(f"[concept] 建边失败: {e}")

        # try:
        #     n_chains = self.store.discover_chains(goal)
        #     if verbose and n_chains > 0:
        #         print(f"[chain] 发现 {n_chains} 条链，已建边")
        # except Exception as e:
        #     if verbose:
        #         print(f"[chain] 失败: {e}")

        # ★ 检索阶段：只跑一轮
        proof = None
        try:
            prover = Prover(self.store, max_depth=12)
            proof = prover.prove(goal, strategy=strategy, var=var,
                                 verbose=False)
            if proof:
                used_ids = [s.clause.id for s in proof]
                self.store.strengthen(used_ids)
                self.store.learn_cooccurrence(used_ids)
                self.store.record_dependency(goal, [s.clause for s in proof])
                if verbose:
                    print(f"  → 成功！强化 {len(used_ids)} 条")
            return proof

        finally:
            self._cleanup_premises(prem_clauses)


def cli():
    import glob
    parser = argparse.ArgumentParser(description="自适应定理证明器")
    parser.add_argument('--prove', type=str, required=True)
    parser.add_argument('--strategy', default='auto',
                        choices=['auto', 'direct', 'contradiction', 'induction'])
    parser.add_argument('--var', type=str, default=None)
    parser.add_argument('--premise', type=str, action='append', default=[])
    parser.add_argument('--stats', action='store_true')
    args = parser.parse_args()

    store = AdaptiveStore()
    if os.path.exists('theorems.jsonl'):
        store.load_jsonl('theorems.jsonl')
    for p in sorted(glob.glob('theorems/*.jsonl')):
        store.load_jsonl(p)
    store.load_weights()
    store.load_dependency_records()

    if args.stats:
        print(store.weight_stats())
        return

    ap = AdaptiveProver(store)
    var = Var(args.var) if args.var else None
    proof = ap.prove(args.prove, strategy=args.strategy, var=var,
                     premises=args.premise, verbose=True)
    print_proof(proof, parse_goal(args.prove))
    store.save_weights()
    store.save_dependency_records()


if __name__ == "__main__":
    cli()