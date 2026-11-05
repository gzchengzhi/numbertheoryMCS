# deep_recursive_prover.py
"""17.0.1 DeepRecursiveProver：深递归 + 索引提速 + 预算控制 + 证明路径固化。

17.0.1 提速：
  - _head_index：按 head 谓词索引神经元，_try_neuron_deep 不遍历全部
  - _clause_head_index：按 head 谓词索引定理，_try_subgoal_split 不跑 retrieve_adaptive 全候选
  - MAX_NODES = 100：单题搜索节点上限，防深度爆炸
  - MAX_RECURSIVE_DEPTH = 6：深度从 8 降到 6
  - ENABLE_SUBGOAL_SPLIT 默认 False，USE_DEEP=1 时显式开

理论对应：
  - Cheng 2019 §8.2.4 上层概念逐层形成
  - Cheng 2019 §8.5.1 E = 2^(N-1)·δ
  - Cheng 2019 §8.5.2 能量约束概念数量
"""
from typing import Optional, List, Dict, Set

from numtheory_prover import (
    parse_goal, parse_term, unify, substitute,
    Var, Const, Pred, HornClause, ProofStep,
)
from recursive_prover import RecursiveProver
from deep_proof import DeepProofStep
from probe import SearchBudgetExceeded


class DeepRecursiveProver(RecursiveProver):
    
    BANNED_IN_SUBGOAL = {"T004", "T005", "T011", "T030"}   # ★ 17.0.1
    MAX_RECURSIVE_DEPTH = 4

    # ★ 17.0.1：单题搜索节点上限
    MAX_NODES = 15

    # ★ 能量预算
    ENERGY_BUDGET = 128.0
    DELTA = 1.0

    # ★ 神经元上限
    MAX_NEURONS_BASE = 1000
    MAX_NEURONS_HARD = 5000
    NEURONS_PER_ENERGY = 10
    MAX_CLAUSES = 5000

    # ★ 子目标分解开关（默认关，USE_DEEP=1 时显式开）
    ENABLE_SUBGOAL_SPLIT = False

    # ★ 16.0.3b：自动学习开关（默认关）
    ENABLE_AUTO_LEARN = False

    def __init__(self, store, max_depth=12, max_nodes=None, max_steps=10,
                 probe=None, verbose=False,
                 iso_edges_path="data/iso_edges.json",
                 energy_budget: Optional[float] = None):
        super().__init__(store, max_depth=max_depth, max_nodes=max_nodes,
                         max_steps=max_steps, probe=probe, verbose=verbose,
                         iso_edges_path=iso_edges_path)
        self.energy_budget = (energy_budget if energy_budget is not None
                              else self.ENERGY_BUDGET)
        self._energy_used = 0.0
        self._nodes_visited = 0
        self._rename_counter = 0
        self._rename_cache = {}
        self._arg_cache = {}
        self._match_head_cache = {}
        self._match_lower_cache = {}

    # ============================================================
    # 索引（17.0.1）
    # ============================================================
    def _build_head_index(self):
        self.store._head_index = {}
        for nid, n in self.store.concept_neurons.items():
            hp = n.get("head_pattern")
            if hp is None:
                continue
            pred = (hp[0] if isinstance(hp, (list, tuple))
                    else str(hp).split("(")[0])
            self.store._head_index.setdefault(pred, []).append(nid)

    def _build_clause_index(self):
        self.store._clause_head_index = {}
        for c in self.store.clauses:
            if c.id.startswith("PREM_"):
                continue
            self.store._clause_head_index.setdefault(c.head.name, []).append(c)

    # ============================================================
    # 公开入口
    # ============================================================
    def prove_deep(self, goal_str: str,
                   premises: Optional[List] = None,
                   verbose: Optional[bool] = None
                   ) -> Optional[DeepProofStep]:
        import time
        self._rename_cache = {}
        self._arg_cache = {}
        self._match_head_cache = {}
        self._match_lower_cache = {} 
        self._subgoal_start = time.time()   # ★ 18.0.1
        
        if len(self.store.concept_neurons) > self._dynamic_neuron_cap():
            raise SearchBudgetExceeded(
                f"neurons {len(self.store.concept_neurons)} > "
                f"cap {self._dynamic_neuron_cap()}")
        if len(self.store.clauses) > self.MAX_CLAUSES:
            raise SearchBudgetExceeded(
                f"clauses {len(self.store.clauses)} > {self.MAX_CLAUSES}")

        if verbose is None:
            verbose = self.verbose
        goal = parse_goal(goal_str)
        if goal is None:
            return None
        prem_preds = self._parse_premises(premises)

        # 建索引（每次重建，防 store 变化后过期）
        self._build_head_index()
        self._build_clause_index()

        self._nodes_visited = 0
        self._energy_used = 0.0
        self._auto_learned_this_call = False

        deep = self._try_deep_chain(goal, prem_preds, _depth=0,
                                    _visited=set())

        # 16.0.3b：失败时自动学习 + 重试
        if deep is None and self.ENABLE_AUTO_LEARN and not self._auto_learned_this_call:
            self._auto_learned_this_call = True
            added = self._auto_learn(goal_str, premises, verbose)
            if added:
                self._nodes_visited = 0
                self._energy_used = 0.0
                deep = self._try_deep_chain(goal, prem_preds, _depth=0,
                                            _visited=set())

        if deep is not None and verbose:
            print(f"[deep] 命中 {deep.strategy}，"
                  f"树深={deep.tree_depth()}，树大小={deep.tree_size()}，"
                  f"节点={self._nodes_visited}，"
                  f"能量={self._energy_used:.2f}/{self.energy_budget:.2f}")
        return deep
    
    def _match_head_pattern(self, hp, goal):
        key = (str(hp), str(goal))
        if key in self._match_head_cache:
            return self._match_head_cache[key]
        result = super()._match_head_pattern(hp, goal)
        self._match_head_cache[key] = result
        return result
    
    def _match_lower(self, low, goal, premises):
        if not isinstance(low, (list, tuple)) or len(low) < 2:
            return super()._match_lower(low, goal, premises)
        low_str = str(low)
        goal_str = str(goal)
        prem_strs = tuple(str(p) for p in premises) if premises else ()
        key = (low_str, goal_str, prem_strs)
        if key in self._match_lower_cache:
            return self._match_lower_cache[key]
        result = super()._match_lower(low, goal, premises)
        self._match_lower_cache[key] = result
        return result

    def prove(self, goal_str: str, premises: Optional[List] = None,
              verbose: Optional[bool] = None) -> Optional[List[ProofStep]]:
        deep = self.prove_deep(goal_str, premises, verbose)
        if deep is not None:
            return deep.to_proof_steps()
        return super().prove(goal_str, premises=premises, verbose=verbose)

    # ============================================================
    # 核心：深递归 + 子目标分解 + 能量预算
    # ============================================================
    def _try_deep_chain(self, goal, premises, _depth, _visited
                        ) -> Optional[DeepProofStep]:
        self._nodes_visited += 1
        if self._nodes_visited > self.MAX_NODES:
            return None
        if _depth > self.MAX_RECURSIVE_DEPTH:
            return None

        step_cost = self._step_energy(_depth)
        if self._energy_used + step_cost > self.energy_budget:
            return None

        cap = self._dynamic_neuron_cap()
        if len(self.store.concept_neurons) > cap:
            return None

        # 1) 图式层直接点火
        direct = self._try_neuron_deep(goal, premises, _depth, _visited)
        if direct is not None:
            self._energy_used += step_cost
            direct.energy_cost = step_cost
            direct.energy_left = self.energy_budget - self._energy_used
            return direct

        # 2) 子目标分解
        # ★ 18.0.1：subgoal_split 只在 _depth == 0 用
        if self.ENABLE_SUBGOAL_SPLIT and _depth == 0:
            split = self._try_subgoal_split(goal, premises, _depth, _visited)
            if split is not None:
                self._energy_used += step_cost
                split.energy_cost = step_cost
                split.energy_left = self.energy_budget - self._energy_used
                return split

        return None

    def _try_neuron_deep(self, goal, premises, _depth, _visited
                         ) -> Optional[DeepProofStep]:
        # 索引 + iso + has_sub 排序
        nids = set(self.store._head_index.get(goal.name, []))
        # 加 iso_index 的 src_nid（其 head 可能不等于 goal.name，但 iso 迁移后才匹配）
        nids |= set(self.iso_index.keys())
        # has_sub 优先
        def has_sub(nid):
            n = self.store.concept_neurons.get(nid, {})
            return any(isinstance(x, str) and x.startswith("NEURON::")
                       for x in n.get("lower", []))
        nids = sorted(nids, key=lambda nid: (not has_sub(nid), nid))
        for nid in nids:
            if nid in _visited:
                continue
            neuron = self.store.concept_neurons.get(nid)
            if neuron is None:
                continue
            hp = neuron.get("head_pattern")
            if hp is None:
                continue
            subst = self._match_head_pattern(hp, goal)
            if subst is None:
                if _depth == 0 and nid in self.iso_index:
                    migrated = self._try_iso_for_nid_deep(
                        nid, goal, premises, _depth, _visited)
                    if migrated is not None:
                        return migrated
                continue

            lowers = neuron.get("lower", [])
            sub_steps: List[DeepProofStep] = []
            ok = True
            for low in lowers:
                if isinstance(low, str) and low.startswith("NEURON::"):
                    sub_goal = self._neuron_head(low)
                    if sub_goal is None:
                        ok = False
                        break
                    sub = self._try_deep_chain(
                        sub_goal, premises, _depth + 1, _visited | {nid})
                    if sub is None:
                        ok = False
                        break
                    sub_steps.append(sub)
                else:
                    if not self._match_lower(low, goal, premises):
                        ok = False
                        break
                    
                    # ★ 17.0.1：裸原子匹配成功，生成 DeepProofStep
                    low_pred = self._lower_to_pred(low)
                    if low_pred is not None:
                        low_pred_subst = substitute(low_pred, subst)
                        for p in premises:
                            if unify(low_pred_subst, p, dict(subst)) is not None:
                                sub_steps.append(DeepProofStep(
                                    clause=HornClause(
                                        "PREM", f"premise {p}", p, [],
                                        category="前提"),
                                    substitution=subst, subgoal=p,
                                    depth=_depth + 1,
                                    strategy="premise"))
                                break
                    
            if not ok:
                continue

            construct = neuron.get("construct")
            if construct:
                subst = self._apply_construct(nid, construct, subst)
                if subst is None:
                    continue
                if not self._verify_construct(nid, construct, subst):
                    continue

            step = DeepProofStep(
                clause=HornClause(nid, f"深递归点火 {nid}", goal, []),
                substitution=subst, subgoal=goal, depth=_depth,
                strategy=f"neuron:{nid}", subgoals=sub_steps)
            return step
        return None
    

    
    def _lower_to_pred(self, low) -> Optional[Pred]:
        if isinstance(low, Pred):
            return low
        if not (isinstance(low, (list, tuple)) and len(low) >= 2):
            return None
        name, args = low[0], low[1]
        terms = []
        for a in args:
            if isinstance(a, str):
                if a.lstrip("-").isdigit():
                    terms.append(Const(a))
                elif len(a) == 1 and a.isalpha():
                    terms.append(Var(a))
                else:
                    terms.append(parse_term(a))
            else:
                terms.append(a)
        return Pred(name, tuple(terms)) 

    def _try_iso_for_nid_deep(self, src_nid, goal, premises, _depth, _visited
                              ) -> Optional[DeepProofStep]:
        for edge in self.iso_index.get(src_nid, []):
            migrated = self._try_iso_migrate_deep(
                edge, goal, premises, _depth, _visited)
            if migrated is not None:
                return migrated
        return None

    def _try_iso_migrate_deep(self, edge, goal, premises, _depth, _visited
                              ) -> Optional[DeepProofStep]:
        dst_nid = edge.get("dst")
        if not dst_nid or dst_nid not in self.store.concept_neurons:
            return None
        if dst_nid in _visited:
            return None
        dst_neuron = self.store.concept_neurons[dst_nid]
        dst_hp = dst_neuron.get("head_pattern")
        if dst_hp is None:
            return None
        subst = self._match_head_pattern(dst_hp, goal)
        if subst is None:
            return None
        if not self._verify_iso(edge, goal):
            return None

        lower_map = edge.get("mapping", {}).get("lower_map")
        dst_lowers = dst_neuron.get("lower", [])
        sub_steps: List[DeepProofStep] = []
        if lower_map:
            if len(lower_map) != len(dst_lowers):
                return None
            for i, lm in enumerate(lower_map):
                dst_low = lm.get("dst")
                src_low = lm.get("src")
                matched = False
                if isinstance(dst_low, (list, tuple)) and self._match_lower(
                        dst_low, goal, premises):
                    matched = True
                elif isinstance(src_low, (list, tuple)) and self._match_lower(
                        src_low, goal, premises):
                    matched = True
                if not matched:
                    return None
                low = dst_lowers[i]
                if isinstance(low, str) and low.startswith("NEURON::"):
                    sub_goal = self._neuron_head(low)
                    if sub_goal is None:
                        return None
                    sub = self._try_deep_chain(
                        sub_goal, premises, _depth + 1, _visited | {dst_nid})
                    if sub is None:
                        return None
                    sub_steps.append(sub)
        else:
            for low in dst_lowers:
                if isinstance(low, str) and low.startswith("NEURON::"):
                    sub_goal = self._neuron_head(low)
                    if sub_goal is None:
                        return None
                    sub = self._try_deep_chain(
                        sub_goal, premises, _depth + 1, _visited | {dst_nid})
                    if sub is None:
                        return None
                    sub_steps.append(sub)
                else:
                    if not self._match_lower(low, goal, premises):
                        return None

        iso_id = edge["id"]
        return DeepProofStep(
            clause=HornClause(
                f"ISO::{iso_id}", f"同构迁移 {iso_id}", goal, [],
                category="同构"),
            substitution=subst, subgoal=goal, depth=_depth,
            strategy=f"iso:{iso_id}", subgoals=sub_steps)

    def _try_subgoal_split(self, goal, premises, _depth, _visited
                           ) -> Optional[DeepProofStep]:
        """子目标分解，用 _clause_head_index 索引，候选上限 50/20。"""
        if _depth > self.MAX_RECURSIVE_DEPTH:
            return None
        # ★ 18.0.1：单层超时 1s
        import time
        if hasattr(self, "_subgoal_start"):
            if time.time() - self._subgoal_start > 1.0:
                return None
        candidates = self.store._clause_head_index.get(goal.name, [])
        candidates = [c for c in candidates
                      if c.id not in self.BANNED_IN_SUBGOAL]
        limit = 20 if _depth == 0 else 10
        candidates = candidates[:limit]
        goal_sig = self._goal_signature(goal)
        for clause in candidates:
            if clause.id.startswith("PREM_"):
                continue
            if (clause.id, goal_sig) in _visited:
                continue
            # ★ 先 unify 原始 head
            if unify(clause.head, goal, {}) is None:
                continue
            renamed = self._rename_clause(clause, _depth)
            subst = unify(renamed.head, goal, {})
            if subst is None:
                continue

            sub_steps: List[DeepProofStep] = []
            ok = True
            current_subst = subst
            for body_pred in renamed.body:
                body_conc = substitute(body_pred, current_subst)
                sub = self._try_deep_chain(
                    body_conc, premises, _depth + 1,
                    _visited | {(clause.id, goal_sig)})
                if sub is None:
                    ok = False
                    break
                sub_steps.append(sub)
                merged = dict(current_subst)
                merged.update(sub.substitution)
                current_subst = merged
            if not ok:
                continue

            return DeepProofStep(
                clause=renamed, substitution=current_subst, subgoal=goal,
                depth=_depth, strategy="subgoal_split", subgoals=sub_steps)
        return None

    # ============================================================
    # 15.0.4：固化成功证明路径为新神经元
    # ============================================================
    def solidify(self, deep: DeepProofStep,
                 weight: Optional[float] = None) -> Optional[str]:
        if deep is None:
            return None
        head_pattern = [deep.subgoal.name,
                        [str(a) for a in deep.subgoal.args]]
        lowers = []
        for sub in deep.subgoals:
            low = self._lower_to_pattern(sub)
            if low is not None:
                lowers.append(low)
        if not lowers:
            return None
        n_level = deep.tree_depth() + 1
        w = weight if weight is not None else 0.5 ** (n_level - 1)
        nid = self._make_neuron_id(head_pattern, lowers, n_level)
        if nid in self.store.concept_neurons:
            return nid
        triangle = {
            "neuron": nid, "type": "single", "lower": lowers,
            "mediator": None, "anchor": None,
            "head_pattern": head_pattern, "N": n_level, "weight": w,
        }
        self.store.add_triangle(triangle, f"SOLIDIFY::{deep.clause.id}")
        if self.verbose:
            print(f"[solidify] {nid}: N={n_level}, weight={w:.3f}")
        return nid

    def _lower_to_pattern(self, step: DeepProofStep):
        if step.strategy.startswith("neuron:"):
            nid = step.strategy.split("neuron:", 1)[1]
            if nid in self.store.concept_neurons:
                return nid
        return [step.subgoal.name, [str(a) for a in step.subgoal.args]]

    def _make_neuron_id(self, head_pattern, lowers, n_level) -> str:
        import hashlib
        key = f"{head_pattern}|{lowers}|N={n_level}"
        h = hashlib.md5(key.encode()).hexdigest()[:8]
        return f"NEURON::SOLID::N{n_level}::{h}"

    def save_solidified(self, path: str = "theorems/concept_neurons.json"):
        self.store.save_neurons(path)

    # ============================================================
    # 16.0.3b：自动学习
    # ============================================================
    def _auto_learn(self, goal_str, premises, verbose) -> int:
        import time
        t0 = time.time()
        try:
            from tools.learn_from_failure import suggest_candidates
            from tools.verify_neuron import verify_by_structure
            from numtheory_prover import HornClause
        except Exception as e:
            if verbose:
                print(f"[auto-learn] import 失败: {e!r}")
            return 0

        cands = suggest_candidates(goal_str, premises or [], self.store)
        if not cands:
            return 0
        added = 0
        for c in cands[:3]:
            if time.time() - t0 > 5.0:
                break
            nid = c["neuron_id"]
            if nid in self.store.concept_neurons:
                continue
            head = self._pattern_to_pred(c["head_pattern"])
            body = [self._pattern_to_pred(lo) for lo in c["lower"]]
            if head is None or any(b is None for b in body):
                continue
            clause = HornClause(
                id=f"VERIFY_{nid}", name="auto-learn verify",
                head=head, body=body)
            if verify_by_structure(clause) is not True:
                continue
            sym_ok = self._verify_by_sympy(clause)
            if sym_ok is False:
                continue
            triangle = {
                "neuron": nid, "type": "single", "lower": c["lower"],
                "mediator": None, "anchor": None,
                "head_pattern": c["head_pattern"], "N": 1, "weight": 1.0,
            }
            self.store.add_triangle(triangle, "AUTO_LEARN")
            added += 1
        return added

    def _pattern_to_pred(self, pat) -> Optional[Pred]:
        from numtheory_prover import parse_term
        if not isinstance(pat, (list, tuple)) or len(pat) < 2:
            return None
        name = pat[0]
        if not isinstance(name, str):
            return None
        args = []
        for a in pat[1]:
            if not isinstance(a, str):
                return None
            if a.lstrip("-").isdigit():
                args.append(Const(a))
            elif len(a) == 1 and a.isalpha():
                args.append(Var(a))
            else:
                args.append(parse_term(a))
        return Pred(name, tuple(args))

    def _verify_by_sympy(self, clause) -> Optional[bool]:
        try:
            from tools.verify_neuron import _has_var, _to_sympy_safe
            import sympy
        except Exception:
            return None
        if _has_var(clause.head) or any(_has_var(b) for b in clause.body):
            return None
        try:
            head_e = _to_sympy_safe(clause.head, self.store)
            if head_e is None:
                return None
            body_e = [_to_sympy_safe(b, self.store) for b in clause.body]
            if any(e is None for e in body_e):
                return None
            combined = sympy.And(*body_e) if body_e else sympy.true
            simp = sympy.simplify(sympy.Implies(combined, head_e))
            if simp == sympy.true:
                return True
            if simp == sympy.false:
                return False
            return None
        except Exception:
            return None

    # ============================================================
    # 能量 / 神经元上限
    # ============================================================
    def _step_energy(self, depth: int) -> float:
        return self.DELTA * (0.5 ** depth)

    def _dynamic_neuron_cap(self) -> int:
        cap = self.MAX_NEURONS_BASE + int(
            self.NEURONS_PER_ENERGY * self._energy_used)
        return min(cap, self.MAX_NEURONS_HARD)

    # ============================================================
    # 辅助
    # ============================================================
    def _parse_premises(self, premises) -> List[Pred]:
        out = []
        for p in (premises or []):
            if isinstance(p, str):
                pg = parse_goal(p)
                if pg is not None:
                    out.append(pg)
            elif isinstance(p, Pred):
                out.append(p)
        return out

    def _goal_signature(self, goal):
        def walk(t):
            tn = type(t).__name__
            if tn == 'Var':
                return 'V'
            if tn == 'Const':
                if not t.args:
                    return f'C:{t.name}'
                return f'F:{t.name}(' + ','.join(walk(a) for a in t.args) + ')'
            if tn == 'Pred':
                return f'P:{t.name}(' + ','.join(walk(a) for a in t.args) + ')'
            return '?'
        return (goal.name, tuple(walk(a) for a in goal.args))
    
    def _arg(self, a):
        """18.0.1 缓存版 _arg（覆盖父类）。
    
        规则与 13.x 一致：
          - 非 str → 原样返回
          - 含 "(" → parse_term
          - 纯数字 → Const
          - 其他 → Var
        缓存 str → 项，防同字符串反复 parse_term。
        """
        if not isinstance(a, str):
            return a
        if a in self._arg_cache:
            return self._arg_cache[a]
        if "(" in a:
            result = parse_term(a)
        elif a.lstrip("-").isdigit():
            result = Const(a)
        else:
            result = Var(a)
        self._arg_cache[a] = result
        return result 

    def _rename_clause(self, clause, depth: int):
        """17.0.1 本地实现 + 18.0.1 缓存。

        - 全局唯一前缀 __v{counter}_，避免同 depth 多次 rename 撞名
        - sum 绑定变量不重命名
        - 缓存 (clause.id, depth) → renamed，防同定理同深度重复 rename
        """
        key = (clause.id, depth)
        if key in self._rename_cache:
            return self._rename_cache[key]

        self._rename_counter += 1
        prefix = f"__v{self._rename_counter}_"
        var_map = {}

        def rename_term(t, bound_names):
            tname = type(t).__name__
            if tname == 'Var':
                if t.name in bound_names:
                    return t
                if t.name not in var_map:
                    var_map[t.name] = Var(f"{prefix}{len(var_map)}")
                return var_map[t.name]
            if tname == 'Const':
                if t.name == "sum" and len(t.args) >= 1:
                    bound_var = t.args[0]
                    bound_name = (bound_var.name
                                  if type(bound_var).__name__ == 'Var'
                                  else None)
                    new_bound = bound_names | ({bound_name}
                                               if bound_name else set())
                    new_args = [bound_var]
                    for a in t.args[1:]:
                        new_args.append(rename_term(a, new_bound))
                    return Const(t.name, tuple(new_args))
                return Const(t.name, tuple(rename_term(a, bound_names)
                                           for a in t.args))
            return t

        def rename_pred(p, bound_names):
            return Pred(p.name, tuple(rename_term(a, bound_names)
                                      for a in p.args))

        new_head = rename_pred(clause.head, set())
        new_body = [rename_pred(b, set()) for b in clause.body]
        result = HornClause(
            id=clause.id, name=clause.name,
            head=new_head, body=new_body,
            category=getattr(clause, 'category', ''),
        )
        self._rename_cache[key] = result
        return result

    def _apply_construct(self, nid, construct, subst):
        try:
            for var_name, expr_str in construct.items():
                if var_name == "verify":
                    continue
                for k in list(subst.keys()):
                    if getattr(k, "name", None) == var_name:
                        constructed = substitute(parse_term(expr_str), subst)
                        subst[k] = constructed
                        break
            return subst
        except Exception as e:
            if self.verbose:
                print(f"[construct] {nid}: {e!r}")
            return None

    def _verify_construct(self, nid, construct, subst) -> bool:
        verify = construct.get("verify", [])
        if not verify:
            return True
        try:
            import sympy
            n_sym = sympy.Symbol("n", integer=True, positive=True)
            for v_str in verify:
                v_pred = parse_goal(v_str)
                if v_pred is None:
                    return False
                v_subst = substitute(v_pred, subst)
                if v_subst.name == "equals" and len(v_subst.args) == 2:
                    # ★ 用 sympy 表达式直接构造，不用 to_sympy
                    lhs = self._term_to_sympy(v_subst.args[0], n_sym)
                    rhs = self._term_to_sympy(v_subst.args[1], n_sym)
                    if lhs is None or rhs is None:
                        return False
                    diff = sympy.simplify(sympy.together(lhs - rhs))
                    if diff != 0:
                        return False
                    continue
                return False
            return True
        except Exception as e:
            if self.verbose:
                print(f"[verify] {nid}: {e!r}")
            return False
    
    def _term_to_sympy(self, t, n_sym):
        """Const/Var → sympy 表达式。"""
        import sympy
        tn = type(t).__name__
        if tn == "Var":
            if t.name == "n":
                return n_sym
            return sympy.Symbol(t.name, integer=True, positive=True)
        if tn == "Const":
            if not t.args:
                return sympy.Symbol(t.name, integer=True, positive=True)
            args = [self._term_to_sympy(a, n_sym) for a in t.args]
            if any(a is None for a in args):
                return None
            if t.name == "plus":
                return sympy.together(args[0] + args[1])
            if t.name == "minus":
                return sympy.together(args[0] - args[1])
            if t.name == "times":
                return args[0] * args[1]
            if t.name == "div":
                return sympy.together(args[0] / args[1])
            if t.name == "power":
                return args[0] ** args[1]
            return None
        return None