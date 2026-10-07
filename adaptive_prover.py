# -*- coding: utf-8 -*-
"""
Created on Tue Oct  6 13:01:48 2026

@author: gzche
"""

"""
自适应证明器：多轮检索 + 权重学习
"""
import os
import argparse
from typing import List, Optional

from numtheory_prover import Prover, parse_goal, Var, ProofStep, print_proof
from adaptive_store import AdaptiveStore


class AdaptiveProver:
    def __init__(self, store: AdaptiveStore, max_rounds: int = 3,
                 base_top_k: int = 20):
        self.store = store
        self.max_rounds = max_rounds
        self.base_top_k = base_top_k

    def prove(self, goal_str: str, strategy: str = "auto",
              var: Optional[Var] = None,
              verbose: bool = True) -> Optional[List[ProofStep]]:
        goal = parse_goal(goal_str)
        if goal is None:
            if verbose:
                print(f"无法解析: {goal_str}")
            return None

        excluded: set = set()
        attempted_ids: List[str] = []

        for round_id in range(self.max_rounds):
            top_k = self.base_top_k * (round_id + 1)    # 20, 40, 60
            expand = min(round_id, 2)      # 0, 1, 2

            relevant = self.store.retrieve_adaptive(
                goal, top_k=top_k, expand_round=expand,
                excluded_ids=excluded,
            )

            if verbose:
                print(f"\n[Round {round_id}] 检索 {len(relevant)} 条 "
                      f"(top_k={top_k}, expand={expand})")
                for c in relevant[:3]:
                    print(f"    {c.id} {c.name} (w={self.store.theorem_weights[c.id]:.2f})")

            if not relevant:
                if verbose:
                    print(f"  → 无候选，跳过")
                continue

            prover = Prover(relevant, max_depth=12)
            proof = prover.prove(goal, strategy=strategy, var=var, verbose=False)

            if proof:
                used_ids = [s.clause.id for s in proof]
                self.store.strengthen(used_ids)
                self.store.learn_cooccurrence(used_ids)
                if verbose:
                    print(f"  → 成功！强化 {len(used_ids)} 条定理 + 共现边")
                return proof

            # 失败 → 把这轮用过的定理加入排除，下轮扩大
            for c in relevant:
                excluded.add(c.id)
            attempted_ids.extend([c.id for c in relevant])
            if verbose:
                print(f"  → 失败，排除 {len(relevant)} 条，扩大检索")

        # 全部失败 → 回退全库
        if verbose:
            print(f"\n[Fallback] 回退到全库（{len(self.store.clauses)} 条）")
        prover = Prover(self.store.clauses, max_depth=12)
        proof = prover.prove(goal, strategy=strategy, var=var, verbose=False)

        if proof:
            used_ids = [s.clause.id for s in proof]
            self.store.strengthen(used_ids)
            self.store.learn_cooccurrence(used_ids)
            return proof

        # 全失败 → 弱化尝试过的定理
        self.store.weaken(attempted_ids)
        self.store.weaken_cooccurrence(attempted_ids)
        if verbose:
            print(f"  → 全部失败，弱化 {len(set(attempted_ids))} 条")
        return None


# ---------- CLI ----------
def cli():
    import glob
    import os

    parser = argparse.ArgumentParser(description="自适应定理证明器")
    parser.add_argument('--data', type=str, nargs='+', default=None,
                        help='JSONL 文件或目录（默认 theorems.jsonl + theorems/*.jsonl）')
    parser.add_argument('--prove', type=str, required=True)
    parser.add_argument('--strategy', choices=['auto', 'direct', 'contradiction', 'induction'],
                        default='auto')
    parser.add_argument('--var', type=str, default=None)
    parser.add_argument('--max_rounds', type=int, default=3)
    parser.add_argument('--reset_weights', action='store_true',
                        help='重置权重')
    parser.add_argument('--stats', action='store_true',
                        help='显示权重统计')
    parser.add_argument('--benchmark', action='store_true',
                        help='批量测试 6 个目标')
    parser.add_argument('--top_k', type=int, default=20,
                        help='首轮检索条数（默认 20）')
    args = parser.parse_args()

    # ---------- 1. 解析 --data ----------
    data_paths = []
    if args.data is None:
        # 默认：theorems.jsonl（如果有）+ theorems/ 下所有 jsonl
        if os.path.exists('theorems.jsonl'):
            data_paths.append('theorems.jsonl')
        data_paths.extend(sorted(glob.glob('theorems/*.jsonl')))
    else:
        for p in args.data:
            if os.path.isdir(p):
                # 目录：取其中所有 jsonl
                data_paths.extend(sorted(glob.glob(os.path.join(p, '*.jsonl'))))
            else:
                data_paths.append(p)

    if not data_paths:
        print("[错误] 没有找到任何 JSONL 文件")
        return

    # ---------- 2. 加载（自动去重） ----------
    store = AdaptiveStore()
    total_loaded = 0
    for path in data_paths:
        if not os.path.exists(path):
            print(f"  [警告] 文件不存在: {path}")
            continue
        before = len(store.clauses)
        store.load_jsonl(path)
        after = len(store.clauses)
        delta = after - before
        total_loaded += delta
        print(f"  加载 {path}: +{delta} 条 (累计 {after})")
    print(f"  [合计] {total_loaded} 条新加载，{len(store.clauses)} 条总库")

    # ---------- 3. 权重处理 ----------
    if args.reset_weights:
        store.theorem_weights.clear()
        print("权重已重置")

    store.load_weights()

    # ---------- 4. 分支 ----------
    if args.stats:
        print("=" * 60)
        print("权重统计")
        print("=" * 60)
        print(store.weight_stats())
        top = sorted(store.theorem_weights.items(), key=lambda x: -x[1])[:10]
        print("\nTop-10 权重:")
        for tid, w in top:
            if w > 1.0 and tid in store.by_id:
                print(f"  {tid}: {w:.2f}  {store.by_id[tid].name}")
        return

    if args.benchmark:
        goals = [
            ("prime(3)", "direct", None),
            ("prime(5)", "direct", None),
            ("irrational(sqrt(2))", "direct", None),
            ("prime_infinite", "contradiction", None),
            ("sum_to_n(1, S)", "direct", None),
            ("sum_to_n(k, S)", "induction", "k"),
        ]
        ap = AdaptiveProver(store, max_rounds=args.max_rounds,
                            base_top_k=args.top_k)
        results = []
        for goal_str, strat, var_name in goals:
            var = Var(var_name) if var_name else None
            print("\n" + "=" * 70)
            print(f"目标: {goal_str}  策略: {strat}")
            print("=" * 70)
            proof = ap.prove(goal_str, strategy=strat, var=var, verbose=True)
            results.append((goal_str, proof is not None))

        print("\n" + "=" * 70)
        print("结果汇总")
        print("=" * 70)
        for g, ok in results:
            print(f"  {'✅' if ok else '❌'}  {g}")

        store.save_weights()
        print(f"\n权重已保存到 theorem_weights.json")
        return

    # 单目标
    ap = AdaptiveProver(store, max_rounds=args.max_rounds,
                        base_top_k=args.top_k)
    var = Var(args.var) if args.var else None
    proof = ap.prove(args.prove, strategy=args.strategy, var=var, verbose=True)
    print_proof(proof, parse_goal(args.prove))

    store.save_weights()


if __name__ == "__main__":
    cli()