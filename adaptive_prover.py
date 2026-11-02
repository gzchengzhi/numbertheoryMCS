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
                 base_top_k: Optional[int] = None,
                 max_depth: int = 12, max_nodes: Optional[int] = None,      # ★ 新增
                 max_steps: int = 10, working_memory=None,
                 probe=None):                           # ★ 新增
        self.store = store
        self.max_rounds = max_rounds
        self.base_top_k = base_top_k
        self.max_nodes = max_nodes
        self.max_depth = max_depth
        self.max_steps = max_steps
        from probe import NoopProbe
        self.probe = probe or NoopProbe()
        from working_memory import NoopWorkingMemory
        self.working_memory = working_memory or NoopWorkingMemory()

        
    def _try_sympy(self, goal):
        
        # ★ 13.0.5: exists(x, P(x)) 的构造性验证
        if goal.name == "exists":
            return self._try_sympy_exists_constructive(goal)
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
        
    def _try_sympy_exists_constructive(self, goal):
        if len(goal.args) != 2:
            return False
        var, body = goal.args
        # 从 concept_neurons 找 construct
        construct = None
        for nid, n in self.store.concept_neurons.items():
            hp = n.get("head_pattern")
            if hp and isinstance(hp, (list, tuple)) and hp[0] == "exists":
                c = n.get("construct")
                if c and var.name in c:
                    construct = c
                    break
        if construct is None:
            return False
        try:
            import sympy
            from sympy_bridge import to_sympy
            from numtheory_prover import parse_term, substitute
            # 用 construct 的 m,n 代入 body
            subst = {}
            for k, expr_str in construct.items():
                subst[Var(k)] = parse_term(expr_str)
            # 只验证 body 里的 equals（代数恒等式）
            body_subst = substitute(body, subst)
            # 递归找 equals
            def check_equals(pred):
                if pred.name == "equals":
                    lhs = to_sympy(pred.args[0], self.store)
                    rhs = to_sympy(pred.args[1], self.store)
                    if lhs is None or rhs is None:
                        return None
                    return sympy.simplify(lhs - rhs) == 0
                if hasattr(pred, "args"):
                    for a in pred.args:
                        if type(a).__name__ == "Pred":
                            r = check_equals(a)
                            if r is not None:
                                return r
                return None
            return check_equals(body_subst) is True
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

    def prove(self, goal_str, strategy="auto", var=None, premises=None, verbose=True):
        # ★ 1. 先 parse_goal，保留 10.0 的 None 检查
        goal = parse_goal(goal_str)
        if goal is None:
            if verbose:
                print(f"无法解析: {goal_str}")
            return None
    
        # ★ 2. probe.start（原逻辑）
        self.probe.start(strategy or "auto")
    
        # ★ 3. 策略选择 + induction 降级
        if strategy == "auto":
            strategy = self._choose_strategy(goal)
            if strategy == "induction" and var is None:
                strategy = "direct"       # 无 var 时降级，修 ValueError
    
        # ★ 4. WM 构造（PR3 已落盘的逻辑，保留）
        from working_memory import WorkingMemory, NoopWorkingMemory, extract_topic
        if not isinstance(self.working_memory, NoopWorkingMemory):
            topic, terms = extract_topic(goal)
            wm = WorkingMemory(topic, terms)
            wm.bind_lookup(lambda nid: self.store.concept_neurons.get(nid))
            self._active_wm = wm
        else:
            self._active_wm = self.working_memory
    
        # ★ 5. 包 _prove_inner，统一 finish
        success, reason = False, ""
        try:
            result = self._prove_inner(goal_str, strategy, var, premises, verbose)
            success = result is not None
            reason = "ok" if success else "no_proof"
            return result
        except Exception as ex:
            reason = f"error: {ex!r}"
            raise
        finally:
            self.probe.finish(success, fell_back=not success, reason=reason)

    def _prove_inner(self, goal_str: str, strategy: str = "auto",
              var: Optional[Var] = None,
              premises: Optional[List[str]] = None,
              verbose: bool = True) -> Optional[List[ProofStep]]:
        goal = parse_goal(goal_str)
        # ★ 主题指导法：为本次证明构造 WM（仅当调用方启用了 WM）
        from working_memory import WorkingMemory, NoopWorkingMemory, extract_topic
        if not isinstance(self.working_memory, NoopWorkingMemory):
            topic, terms = extract_topic(goal)
            wm = WorkingMemory(topic, terms)
            wm.bind_lookup(lambda nid: self.store.concept_neurons.get(nid))
            self._active_wm = wm
        else:
            self._active_wm = self.working_memory
            
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
            prover = Prover(self.store, max_depth=self.max_depth,
                max_nodes=self.max_nodes, probe=self.probe)
            prover.max_steps = self.max_steps
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
            prover = Prover(self.store, max_depth=self.max_depth,
                max_nodes=self.max_nodes, probe=self.probe)
            prover.max_steps = self.max_steps
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
        
        # ★ WM 过滤：得到与主题相关的神经元 id 集合
        wm = getattr(self, "_active_wm", None)
        if wm is not None and wm.topic:
            related = set()
            for nid, neuron in self.store.concept_neurons.items():
                if wm.relevance(neuron) > 0.0:
                    related.add(nid)
            if not related:
                # 主题无相关神经元：直接放弃神经元层，回退链式（不消耗 energy）
                return None
        else:
            related = None   # None = 不过滤（Noop WM）

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
                if related is not None and nid not in related:   # ★ WM 过滤
                    continue
                
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
    # adaptive_prover.py cli() 里，load_dependency_records() 之后加
    store.load_neurons("theorems/concept_neurons.json")

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