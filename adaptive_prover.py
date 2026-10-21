"""
自适应证明器：一次检索 + 一次学习 + 概念多边形建边 + 链式建边 + 独立依赖记录
"""
import os
import argparse
from typing import List, Optional

from numtheory_prover import (
    Prover, parse_goal, Var, ProofStep, print_proof, HornClause, substitute
)
from adaptive_store import AdaptiveStore


class AdaptiveProver:
    def __init__(self, store: AdaptiveStore, max_rounds: int = 1,
                 base_top_k: Optional[int] = None):
        self.store = store
        self.max_rounds = max_rounds       # ★ 默认 1，只跑一轮
        self.base_top_k = base_top_k        # ★ 默认 None，返回全部
        
    def _try_sympy(self, goal):
        """尝试直接用 sympy 解决目标"""
        from sympy_bridge import to_sympy
        import sympy
        
        # 只对特定谓词尝试 sympy 计算，避免无谓的开销
        if goal.name not in ('irrational', 'prime', 'congruent', 'divides', 'Eq', 'coprime', 'gt', 'ge', 'lt', 'le'):
            return False
            
        try:
            # 把目标翻译成 sympy 表达式
            expr = to_sympy((goal.name, tuple(str(a) for a in goal.args)), self.store)
            if expr is None:
                return False
                
            # 计算并化简
            result = sympy.simplify(expr)
            
            # 如果结果是 True
            if bool(result) is True:
                return True
            return False
        except Exception:
            return False

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
                    
    def _choose_strategy(self, goal):
        """
        根据目标谓词和结构，启发式选择最优策略（注意力控制）。
        """
        pred = goal.name
        
        # 1. 存在性/全称/无理性：必须优先反证法
        if pred in ('exists', 'forall', 'irrational', 'not_prime_decomposable'):
            return 'contradiction'
        
        # 2. 数论典型结论：优先 direct（往往有传递性或定义）
        if pred in ('congruent', 'divides', 'prime', 'coprime'):
            return 'direct'
        
        # 3. 求值/等式证明：优先归纳或直接
        if pred in ('equals', 'sum_to_n', 'sum_of_squares'):
            return 'induction'
        
        # 4. 默认使用 direct
        return 'direct'                    

    def prove(self, goal_str: str, strategy: str = "auto",
              var: Optional[Var] = None,
              premises: Optional[List[str]] = None,
              verbose: bool = True) -> Optional[List[ProofStep]]:
        goal = parse_goal(goal_str)
        if goal is None:
            if verbose:
                print(f"无法解析: {goal_str}")
            return None

        # ★ 第一优先级：sympy 直接计算（无论 strategy 是什么）
        if self._try_sympy(goal):
            if verbose:
                print(f"[sympy] 直接计算成功: {goal}")
            from numtheory_prover import ProofStep, HornClause
            step = ProofStep(
                clause=HornClause("SYMPY", "sympy 计算", goal, [], category="计算"),
                substitution={},
                subgoal=goal,
                depth=0,
                strategy="sympy",
            )
            return [step]

        # ★ 第二优先级：注意力控制（自动选策略）
        if strategy == 'auto':
            strategy = self._choose_strategy(goal)
            if verbose:
                print(f"[strategy] 自动选择策略: {strategy}")

        # 下面才是原来的神经元激活 / 链式推理
        ...

        # ★ 物理层/计算层优先：尝试直接 sympy 算
        if self._try_sympy(goal):
            if verbose:
                print(f"[sympy] 直接计算成功: {goal}")
            from numtheory_prover import ProofStep, HornClause
            # 构造一个虚拟的证明步骤
            step = ProofStep(
                clause=HornClause("SYMPY", "sympy 计算", goal, [], category="计算"),
                substitution={},
                subgoal=goal,
                depth=0,
                strategy="sympy",
            )
            return [step]
                

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
        prem_preds = [c.head for c in prem_clauses]

        # ★ 10.0 新增：先试神经元激活
        try:
            neuron_result = self._try_activate_neurons(goal, prem_preds)
            if neuron_result is not None:
                if verbose:
                    print(f"[neuron] 通过神经元激活：{neuron_result['via']}")
                proof = neuron_result['proof']
                used_ids = [s.clause.id for s in proof]
                self.store.strengthen(used_ids)
                self.store.learn_cooccurrence(used_ids)
                self.store.record_dependency(goal, [s.clause for s in proof])
                return proof
        except Exception as e:
            if verbose:
                print(f"[neuron] 激活失败: {e}")


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

    def _const_to_var(self, pred):
        """把 Pred 里单字母的 Const 转成 Var"""
        from numtheory_prover import Var, Const, Pred
        
        def convert(t):
            tn = type(t).__name__
            if tn == 'Const':
                if len(t.name) == 1 and t.name.isalpha() and not t.args:
                    return Var(t.name)
                return Const(t.name, tuple(convert(a) for a in t.args))
            if tn == 'Pred':
                return Pred(t.name, tuple(convert(a) for a in t.args))
            return t
        
        return Pred(pred.name, tuple(convert(a) for a in pred.args))    

    def _rename_for_neuron(self, clause):
        """重命名 clause 的变量为 q0, q1, q2...，返回 (renamed_clause, back_map)"""
        from numtheory_prover import HornClause, Var, Const, Pred
        
        counter = [0]
        var_map = {}
        back_map = {}
        
        def rename_term(t):
            tn = type(t).__name__
            if tn == 'Var':
                if t.name not in var_map:
                    new_name = f"q{counter[0]}"
                    var_map[t.name] = Var(new_name)
                    back_map[new_name] = t.name
                    counter[0] += 1
                return var_map[t.name]
            if tn == 'Const':
                return Const(t.name, tuple(rename_term(a) for a in t.args))
            if tn == 'Pred':
                return Pred(t.name, tuple(rename_term(a) for a in t.args))
            return t
        
        def rename_pred(p):
            return Pred(p.name, tuple(rename_term(a) for a in p.args))
        
        renamed = HornClause(
            id=clause.id,
            name=clause.name,
            head=rename_pred(clause.head),
            body=[rename_pred(b) for b in clause.body],
            category=clause.category,
        )
        return renamed, back_map         
            
    def _try_activate_neurons(self, goal, premises):
        if not self.store.concept_neurons:
            return None

        from concept_triangle import extract_triangles
        from sympy_bridge import to_sympy
        from numtheory_prover import unify, ProofStep, Var, Const, Pred

        # 1. 提取骨架（用于快速匹配）
        def pattern(p):
            vars_seen = {}
            counter = [0]
            def walk(t):
                if isinstance(t, Var):
                    if t.name not in vars_seen:
                        vars_seen[t.name] = f"v{counter[0]}"
                        counter[0] += 1
                    return vars_seen[t.name]
                if isinstance(t, Const):
                    if not t.args:
                        return f"C:{t.name}"
                    return f"F:{t.name}(" + ",".join(walk(a) for a in t.args) + ")"
                return "?"
            return (p.name, tuple(walk(a) for a in p.args))

        prem_patterns = [pattern(p) for p in premises]
        goal_pattern = pattern(goal)

        # 2. 遍历定理，找拓扑结构一致的
        for c in self.store.clauses:
            if c.head.name != goal.name:
                continue

            # 检查 body 的模式是否和 premises 一致
            c_body_patterns = [pattern(b) for b in c.body]
            if sorted(prem_patterns) != sorted(c_body_patterns):
                continue

            # ★ 核心修复：检查 head 能不能匹配 goal
            subst = unify(c.head, goal, {})
            if subst is None:
                continue
            # 过滤自映射
            subst = {k: v for k, v in subst.items() if k != v}

            # 跑 extract_triangles 看生成的神经元
            r = extract_triangles(c, to_sympy, self.store)
            if not r['triangles']:
                continue

            for tri in r['triangles']:
                nid = tri['neuron']
                if nid in self.store.concept_neurons:
                    step = ProofStep(
                        clause=c,
                        substitution=subst,
                        subgoal=goal,
                        depth=0,
                        strategy=f'neuron:{nid}',
                    )
                    return {
                        'via': nid,
                        'proof': [step],
                    }
        return None


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