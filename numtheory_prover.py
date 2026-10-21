"""
数论定理自动证明 v3（反证法 + 归纳法）

修复：
  1. parse_goal 支持零参数谓词
  2. 反证法：假设 NOT goal，直接找 contradiction 证明链
  3. 归纳法：正确处理自由变量
  4. auto 策略：直接 → 反证 → 归纳
"""

import os
import re
import argparse
from typing import List, Dict, Tuple, Optional, Set, Any
from dataclasses import dataclass
#from adaptive_store import AdaptiveStore

# ============================================================
# 一、项与公式
# ============================================================

@dataclass(frozen=True)
class Var:
    name: str
    def __repr__(self):
        return self.name


@dataclass(frozen=True)
class Const:
    name: str
    args: Tuple = ()
    def __repr__(self):
        if not self.args:
            return self.name
        return f"{self.name}({','.join(map(str, self.args))})"


@dataclass(frozen=True)
class Pred:
    name: str
    args: Tuple = ()
    def __repr__(self):
        if not self.args:
            return self.name
        return f"{self.name}({','.join(map(str, self.args))})"

    def __post_init__(self):
        # 防止 args 被包装成 ((...),)
        if self.args and len(self.args) == 1 and isinstance(self.args[0], tuple):
            object.__setattr__(self, 'args', self.args[0])
        



def make_var(name): return Var(name)
def make_const(name, *args): return Const(name, args)
def make_pred(name, *args): return Pred(name, args)


# ============================================================
# 二、合一
# ============================================================

def is_var(x):
    return type(x).__name__ == 'Var'

def occurs_check(v, term):
    tname = type(term).__name__
    if tname == 'Var':
        return v == term
    if tname in ('Const', 'Pred'):
        return any(occurs_check(v, a) for a in term.args)
    return False


def substitute(term, subst):
    tname = type(term).__name__
    if tname == 'Var':
        if term in subst:
            replacement = subst[term]
            # ★ 防无限递归：如果替换的值就是自己（同名 Var），直接返回
            if type(replacement).__name__ == 'Var' and replacement.name == term.name:
                return term
            return substitute(replacement, subst)
        return term
    if tname == 'Const':
        if not term.args:
            return term
        return Const(term.name, tuple(substitute(a, subst) for a in term.args))
    if tname == 'Pred':
        return Pred(term.name, tuple(substitute(a, subst) for a in term.args))
    return term


def _type_name(term):
    return type(term).__name__

def unify(t1, t2, subst=None):
    if subst is None:
        subst = {}

    t1 = substitute(t1, subst)
    t2 = substitute(t2, subst)

    if t1 == t2:
        return subst

    t1_type = _type_name(t1)
    t2_type = _type_name(t2)

    # Var 分支
    if t1_type == 'Var':
        if occurs_check(t1, t2):
            return None
        new = dict(subst); new[t1] = t2; return new
    if t2_type == 'Var':
        if occurs_check(t2, t1):
            return None
        new = dict(subst); new[t2] = t1; return new

    # Const 分支
    if t1_type == 'Const' and t2_type == 'Const':
        if t1.name != t2.name or len(t1.args) != len(t2.args):
            from symbolic import math_equivalent
            if math_equivalent(t1, t2):
                return subst
            return None
        for a1, a2 in zip(t1.args, t2.args):
            subst = unify(a1, a2, subst)
            if subst is None:
                return None
        return subst

    # Pred 分支
    if t1_type == 'Pred' and t2_type == 'Pred':
        if t1.name != t2.name or len(t1.args) != len(t2.args):
            return None
        for a1, a2 in zip(t1.args, t2.args):
            subst = unify(a1, a2, subst)
            if subst is None:
                return None
        return subst

    return None

def _collect_var_names_helper(term) -> set:
    result = set()
    tname = type(term).__name__
    #print(f"[collect] term={term}, tname={tname}")
    if tname == 'Var':
        result.add(term.name)
    elif tname in ('Const', 'Pred'):
        for a in term.args:
            result |= _collect_var_names_helper(a)
    return result



# ============================================================
# 三、Horn 子句
# ============================================================

@dataclass
class HornClause:
    id: str
    name: str
    head: Pred
    body: List[Pred]
    proof_hint: str = ""
    category: str = ""

    def __repr__(self):
        if not self.body:
            return f"{self.id} {self.name}: {self.head}."
        body_str = ", ".join(map(str, self.body))
        return f"{self.id} {self.name}: {self.head} :- {body_str}."


# ============================================================
# 四、定理库
# ============================================================

def build_theorem_db() -> List[HornClause]:
    return []


# ============================================================
# 五、证明器
# ============================================================

@dataclass
class ProofStep:
    clause: HornClause
    substitution: Dict[Var, Any]
    subgoal: Pred
    depth: int
    strategy: str = "direct"



class Prover:

    def __init__(self, store, max_depth: int = 12):
        # 兼容两种用法：
        # 1. store 是 List[HornClause]（旧用法）
        # 2. store 是 AdaptiveStore（新用法，有 retrieve_adaptive 方法）
        if isinstance(store, list):
            self.store = None
            self.db = store
        else:
            self.store = store
            self.db = store.clauses
        self.max_depth = max_depth
        self.step_count = 0
        self.max_steps = 10
        self.visited: Set[str] = set()
        self._rename_counter = 0   # ★ 全局唯一前缀计数器
        
    def _to_skolem_pred(self, pred, all_vars):
        """把谓词里的所有变量转成 Skolem 常量"""
        def convert(t):
            if isinstance(t, Var):
                return Const(f"SKOLEM_{t.name}")
            if isinstance(t, Const):
                return Const(t.name, tuple(convert(a) for a in t.args))
            return t
        return Pred(pred.name, tuple(convert(a) for a in pred.args))
    
    def _collect_vars(self, term) -> set:
        """收集项里的所有变量名"""
        result = set()
        def walk(t):
            if isinstance(t, Var):
                result.add(t.name)
            elif isinstance(t, Const):
                for a in t.args:
                    walk(a)
            elif isinstance(t, Pred):
                for a in t.args:
                    walk(a)
        walk(term)
        return result

    # -------- 直接证明 --------
    def prove_direct(self, goal: Pred) -> Optional[List[ProofStep]]:
        self.step_count = 0
        self.visited = set()
        return self._prove_recursive(goal, {}, 0, [], strategy="direct")

    def _rename_clause(self, clause: HornClause, depth: int) -> HornClause:
        # ★ 全局唯一前缀，避免同 depth 多次 rename 撞名
        self._rename_counter += 1
        prefix = f"__v{self._rename_counter}_"

        var_map = {}

        def rename_term(t, bound_names: set):
            """bound_names: 当前作用域内的绑定变量名集合，不重命名"""
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
                    bound_name = bound_var.name if type(bound_var).__name__ == 'Var' else None
                    new_bound_names = bound_names | ({bound_name} if bound_name else set())
                    new_args = [bound_var]
                    for a in t.args[1:]:
                        new_args.append(rename_term(a, new_bound_names))
                    return Const(t.name, tuple(new_args))
                return Const(t.name, tuple(rename_term(a, bound_names) for a in t.args))
            return t

        def rename_pred(p, bound_names: set):
            return Pred(p.name, tuple(rename_term(a, bound_names) for a in p.args))

        new_head = rename_pred(clause.head, set())
        new_body = [rename_pred(b, set()) for b in clause.body]

        return HornClause(
            id=clause.id,
            name=clause.name,
            head=new_head,
            body=new_body,
            category=clause.category,
        )
    
    def _goal_signature(self, goal):
        """goal 的结构签名：忽略变量名，只看结构。
        - Const 保留名字：C:a
        - Var 统一记作 V
        - 复合表达式递归：F:plus(C:a,C:c)
        """
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
        if type(goal).__name__ != 'Pred':
            return ('?', ())
        return (goal.name, tuple(walk(a) for a in goal.args))

    def _prove_recursive(self, goal, subst, depth, path, strategy="direct",
                         extra_db=None, energy=10.0, strict_prem=True):
        # ★ 改动 1：签名加 strict_prem=True
        if energy < 0.5 ** depth:
            return None
        energy = energy - 0.5 ** depth

        self.step_count += 1
        if self.step_count > self.max_steps:
            return None
        if depth > self.max_depth:
            return None

        goal = substitute(goal, subst)

        # ★ 符号不等式处理
        if goal.name in ("gt", "ge", "lt", "le", "ne"):
            lhs = goal.args[0] if goal.args else None
            has_factorial = False

            def _check_factorial(t):
                nonlocal has_factorial
                tn = type(t).__name__
                if tn == 'Const' and t.name == "factorial":
                    has_factorial = True
                elif tn in ('Const', 'Pred'):
                    for a in t.args:
                        _check_factorial(a)

            _check_factorial(goal)

            if lhs is not None and not has_factorial:
                try:
                    from symbolic import (
                        prove_inequality_symbolic,
                        collect_constraints,
                    )
                    var_names = set()
                    for a in goal.args:
                        var_names |= _collect_var_names_helper(a)

                    db_for_constraints = extra_db if extra_db is not None else self.db
                    constraints = {}
                    for vn in var_names:
                        constraints[vn] = collect_constraints(db_for_constraints, vn)

                    result = prove_inequality_symbolic(goal, constraints)
                    if result is True:
                        sym_clause = HornClause(
                            "SYM_INEQ", f"符号不等式: {goal}", goal, [],
                            "符号不等式"
                        )
                        step = ProofStep(sym_clause, {}, goal, depth, "symbolic")
                        return path + [step]
                except Exception:
                    pass

        # 计算引擎
        try:
            from arithmetic_engine import evaluate_predicate
            result = evaluate_predicate(goal)
            if result is True:
                return path + [ProofStep(
                    HornClause("COMPUTED", f"计算: {goal}", goal, [], "计算"),
                    {}, goal, depth, strategy)]
            elif result is False:
                return None
        except Exception:
            pass

        # 候选收集
        if self.store is not None:
            candidates = self.store.retrieve_adaptive(goal, top_k=None)
            store_ids = {c.id for c in self.store.clauses}
            extra = [c for c in self.db if c.id not in store_ids]
            if extra_db is not None:
                extra_db_ids = {c.id for c in extra_db}
                store_extra = [
                    c for c in extra_db
                    if c.id not in store_ids
                    and c.id not in {c2.id for c2 in extra}
                ]
                extra = extra + store_extra
            # ★ 改动 5：保留 retrieve_adaptive 顺序，extra 在前
            candidates = extra + candidates
        else:
            candidates = self.db

            def _count_top_vars(t):
                if type(t).__name__ != 'Pred':
                    return 0
                return sum(1 for a in t.args if type(a).__name__ == 'Var')
            candidates = sorted(candidates, key=lambda c: -_count_top_vars(c.head))

                # ★ 细粒度去重：记录 (clause_id, goal_sig) 对
        used_goals = set()
        for step in path:
            step_sig = self._goal_signature(step.subgoal)
            used_goals.add((step.clause.id, step_sig))

        def _unify_prem(prem_head, goal, subst):
            """严格模式：前提的 Var 必须都在 goal 里同名出现"""
            def collect_vars(t, acc):
                tn = type(t).__name__
                if tn == 'Var':
                    acc.add(t.name)
                elif tn in ('Const', 'Pred'):
                    for a in t.args:
                        collect_vars(a, acc)
            prem_vars = set()
            collect_vars(prem_head, prem_vars)
            goal_vars = set()
            collect_vars(goal, goal_vars)
            for vn in prem_vars:
                if vn not in goal_vars:
                    return None
            return unify(prem_head, goal, subst)

        #used_ids = {step.clause.id for step in path}
        for clause in candidates:


            #print(f"[TRY] d={depth} {clause.id} goal={goal}")   # ★ 加
            # ★ 同 clause 在同结构 goal 上用过才跳过
            goal_sig = self._goal_signature(goal)
            if (clause.id, goal_sig) in used_goals:
                continue

            renamed_clause = self._rename_clause(clause, depth)
            #print(f"[TRY] d={depth} {clause.id} goal={goal}")   # 加回来
            # ★ 改动 3：只有"严格模式 + PREM"才走 _unify_prem
            if clause.id.startswith("PREM_") and strict_prem:
                new_subst = _unify_prem(renamed_clause.head, goal, dict(subst))
            else:
                new_subst = unify(renamed_clause.head, goal, dict(subst))
            # ★ 改动 2：删掉了重复的 unify 调用

            if new_subst is None:
                #print(f"[FAIL] {clause.id}")                    # 加回来                
                continue
            #print(f"[OK] {clause.id} subst={new_subst}")        # 加回来

            step = ProofStep(renamed_clause, new_subst, goal, depth, strategy)
            new_path = path + [step]

            if not renamed_clause.body:
                #print(f"[NO_BODY] {clause.id}")                 # 加回来
                return new_path
            #print(f"[BODY] {clause.id} {renamed_clause.body}")  # 加回来

            body_success = True
            body_path = new_path
            current_subst = new_subst

            for body_pred in renamed_clause.body:
                body_pred_subst = substitute(body_pred, current_subst)
                # ★ 改动 4：body 递归传 strict_prem=False
                result = self._prove_recursive(
                    body_pred_subst, current_subst, depth + 1, body_path,
                    strategy=strategy, extra_db=extra_db,
                    energy=energy,
                    strict_prem=False,
                )
                if result is None:
                    body_success = False
                    break
                body_path = result
                if result:
                    merged = dict(current_subst)
                    merged.update(result[-1].substitution)
                    current_subst = merged

            if body_success:
                return body_path

        return None
    
    def _head_specificity(clause):
        """head 里 Const 越多，越具体，优先级越高"""
        def count_const(t):
            tn = type(t).__name__
            if tn == 'Const':
                return 1 + sum(count_const(a) for a in t.args)
            if tn in ('Const', 'Pred'):
                return sum(count_const(a) for a in t.args)
            return 0
        return -count_const(clause.head)  # 负号：Const 多的排前面
    
    def _prove_exists_constructive(self, goal, subst, depth, path, strategy, extra_db):
        """
        尝试构造性地证明 exists(p, P(p))。
        对具体值，用小范围搜索。
        """
        from arithmetic_engine import evaluate_predicate
        from symbolic import extract_search_range
    
        if len(goal.args) != 2:
            return None
    
        var = goal.args[0]
        body = goal.args[1]
    
        # 检查其他变量是否都是具体值
        other_vars = _collect_var_names_helper(body) - {var.name}
        if other_vars:
            return None
    
        # 提取搜索范围
        lower, upper = extract_search_range(body, var.name)
    
        def _to_int(t):
            if t is None:
                return None
            try:
                from arithmetic_engine import evaluate
                v = evaluate(t)
                if isinstance(v, int):
                    return v
            except Exception:
                pass
            return None
    
        lo = _to_int(lower)
        up = _to_int(upper)
    
        if lo is None:
            lo = 0
        if up is None:
            up = 1000
        up = min(up, 10000)
    
        # 搜索
        for p_val in range(lo + 1, up):
            p_const = Const(str(p_val))
            instantiated = substitute(body, {var: p_const})
            try:
                result = evaluate_predicate(instantiated)
                if result is True:
                    # 找到！
                    construct_clause = HornClause(
                        "CONSTRUCT", f"构造: {var.name}={p_val}",
                        Pred("equals", (var, p_const)), [], category="构造"
                    )
                    step = ProofStep(construct_clause, {}, goal, depth, "construct")
                    return path + [step]
            except Exception:
                continue
    
        return None
    
    def _prove_exists(self, goal, subst, depth, path, strategy, extra_db):
        if depth > 3:
            return None
    
        db = extra_db if extra_db is not None else self.db
    
        for clause in db:
            if type(clause.head).__name__ != 'Pred':
                continue
            if clause.head.name != "exists":
                continue
    
            renamed_clause = self._rename_clause(clause, depth)
            new_subst = unify(renamed_clause.head, goal, dict(subst))
            if new_subst is None:
                continue
    
            step = ProofStep(renamed_clause, new_subst, goal, depth, strategy)
            new_path = path + [step]
    
            if not renamed_clause.body:
                return new_path
    
            body_success = True
            body_path = new_path
            current_subst = new_subst
    
            for body_pred in renamed_clause.body:
                body_pred_subst = substitute(body_pred, current_subst)
                result = self._prove_recursive(
                    body_pred_subst, current_subst, depth + 1, body_path,
                    strategy=strategy, extra_db=extra_db
                )
                if result is None:
                    body_success = False
                    break
                body_path = result
                if result:
                    merged = dict(current_subst)
                    merged.update(result[-1].substitution)
                    current_subst = merged
    
            if body_success:
                # ★ 新增：把存在变量绑定到 Skolem 常量
                original_exists_var = clause.head.args[0]
                if type(original_exists_var).__name__ == 'Var':
                    # 收集 goal 里除 exists 变量外的自由变量
                    free_vars = []
                    def _collect(t):
                        if type(t).__name__ == 'Var' and t.name != original_exists_var.name:
                            if t not in free_vars:
                                free_vars.append(t)
                        elif type(t).__name__ in ('Const', 'Pred'):
                            for a in t.args:
                                _collect(a)
                    _collect(goal)
                    
                    skolem_name = f"SKOLEM_{original_exists_var.name}"
                    skolem_const = Const(skolem_name, tuple(free_vars))  # ← 带参数

                    skolem_clause = HornClause(
                        "SKOLEM", f"Skolem化: {original_exists_var.name}={skolem_name}",
                        goal, [], category="Skolem"
                    )
                    skolem_step = ProofStep(
                        skolem_clause,
                        {original_exists_var: skolem_const},
                        goal,
                        depth,
                        "skolem"
                    )
                    body_path = body_path + [skolem_step]
                return body_path
    
        return None

    # -------- 反证法 --------
    def prove_by_contradiction(self, goal: Pred,
                               verbose: bool = False) -> Optional[List[ProofStep]]:
        if goal.name.startswith("not_"):
            return None

        negated = Pred("not_" + goal.name, goal.args)
        assumption = HornClause(
            "ASSUME", f"假设 {negated}",
            negated, [], category="反证法假设",
        )
        temp_db = self.db + [assumption]

        if verbose:
            print(f"  [反证法] 假设: {negated}")

        self.step_count = 0
        self.visited = set()
        contra = Pred("contradiction", ())
        proof = self._prove_recursive(contra, {}, 0, [],
                                      strategy="contradiction",
                                      extra_db=temp_db)

        # ---- 关键修复：验证证明链必须包含 ASSUME ----
        if proof is not None:
            used_ids = {step.clause.id for step in proof}
            if "ASSUME" not in used_ids:
                if verbose:
                    print(f"  [反证法] 证明链未用到假设，判定失败")
                return None
            if verbose:
                print(f"  [反证法] 推出 contradiction（用到假设）")

        return proof

    # -------- 归纳法 --------
    def prove_by_induction(self, goal: Pred, var: Var,
                       base_value: str = "1",
                       verbose: bool = False) -> Optional[List[ProofStep]]:
        if verbose:
            print(f"  [归纳法] 变量: {var}")
    
        # ---- 基例 ----
        base_goal = substitute(goal, {var: Const(base_value)})
        if verbose:
            print(f"  [归纳法] 基例: {base_goal}")
    
        self.step_count = 0
        self.visited = set()
        base_proof = self._prove_recursive(base_goal, {}, 0, [], strategy="direct")
    
        if base_proof is None:
            if verbose:
                print(f"  [归纳法] 基例失败")
            return None
        if verbose:
            print(f"  [归纳法] 基例成功")
    
        # ---- 归纳步 ----
        k_var = Var("__k")
        s_var = Var("__s")

        ih_clause = HornClause("IH", "归纳假设",
                               make_pred("sum_to_n", k_var, s_var),
                               [], category="归纳")
        temp_db = self.db + [ih_clause]
        
        next_goal = substitute(goal, {var: Const("plus", (k_var, Const("1")))})
        
        self.step_count = 0
        self.visited = set()
        ind_proof = self._prove_recursive(next_goal, {}, 0, [],
                                          strategy="induction",
                                          extra_db=temp_db)
        temp_db = self.db + [ih_clause]
    
        self.step_count = 0
        self.visited = set()
        ind_proof = self._prove_recursive(next_goal, {}, 0, [],
                                          strategy="induction",
                                          extra_db=temp_db)
    
        if ind_proof is None:
            if verbose:
                print(f"  [归纳法] 归纳步失败")
            return None
        if verbose:
            print(f"  [归纳法] 归纳步成功")
    
        return base_proof + ind_proof

    # -------- 统一入口 --------
    def prove(self, goal, strategy="auto", var=None, base_value="1", verbose=False):
    # 关键修复：每次证明前重新排序
        self.db = sorted(self.db, key=lambda c: len(c.body))

        if strategy == "direct":
            self.step_count = 0
            self.visited = set()
            return self._prove_recursive(goal, {}, 0, [], strategy="direct")

        if strategy == "contradiction":
            return self.prove_by_contradiction(goal, verbose)

        if strategy == "induction":
            if var is None:
                raise ValueError("归纳法必须指定 --var")
            return self.prove_by_induction(goal, var, base_value, verbose)

        # auto: 直接 → 反证 → 归纳
        if verbose:
            print(f"  [auto] 尝试直接证明...")
        proof = self.prove_direct(goal)
        if proof:
            return proof

        if verbose:
            print(f"  [auto] 直接失败，尝试反证法...")
        proof = self.prove_by_contradiction(goal, verbose)
        if proof:
            return proof

        if var is not None:
            if verbose:
                print(f"  [auto] 反证失败，尝试归纳法...")
            proof = self.prove_by_induction(goal, var, base_value, verbose)
            if proof:
                return proof

        return None
    
    def prove_with_premises(self, goal, premises, strategy="auto",
                            var=None, base_value="1", verbose=False):
        temp_clauses = []
        for i, p in enumerate(premises):
            temp_clauses.append(HornClause(
                f"PREM_{i}", f"前提 {p}", p, [], category="前提"
            ))
        saved_db = self.db
        self.db = list(self.db) + temp_clauses
        
        # ★ 同时加入 store.clauses，保证 retrieve_adaptive 能返回
        if self.store is not None:
            for c in temp_clauses:
                if c.id not in self.store.by_id:
                    self.store.clauses.append(c)
                    self.store.by_id[c.id] = c
                    if hasattr(self.store, 'by_predicate'):
                        self.store.by_predicate[c.head.name].append(c.id)
        try:
            proof = self.prove(goal, strategy=strategy, var=var,
                               base_value=base_value, verbose=verbose)
        finally:
            self.db = saved_db
            # 清理
            if self.store is not None:
                for c in temp_clauses:
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
        return proof

# ============================================================
# 六、输出
# ============================================================

def print_proof(proof: List[ProofStep], goal: Pred):
    if not proof:
        print("未能证明。")
        return

    print("\n" + "=" * 60)
    print("证明链:")
    print("=" * 60)

    strategies = set(s.strategy for s in proof)
    if "contradiction" in strategies:
        print("【策略：反证法】")
    if "induction" in strategies:
        print("【策略：数学归纳法】")

    for i, step in enumerate(proof, 1):
        indent = "  " * min(step.depth, 3)
        print(f"{indent}[{i}] 应用「{step.clause.name}」（{step.clause.id}）")
        if step.clause.body:
            body_str = ", ".join(str(substitute(b, step.substitution)) for b in step.clause.body)
            print(f"{indent}    前提: {body_str}")
        head_str = substitute(step.clause.head, step.substitution)
        print(f"{indent}    结论: {head_str}")

    print("\n" + "=" * 60)
    print(f"证明成功：{goal}")
    print("=" * 60)


# ============================================================
# 七、解析输入
# ============================================================

# def parse_term(t: str):
#     t = t.strip()
#     # 嵌套函数/常量：name(args...)
#     m = re.match(r'(\w+)\((.+)\)', t)
#     if m:
#         inner = []
#         depth = 0
#         cur = ""
#         for ch in m.group(2):
#             if ch == '(':
#                 depth += 1; cur += ch
#             elif ch == ')':
#                 depth -= 1; cur += ch
#             elif ch == ',' and depth == 0:
#                 inner.append(cur.strip()); cur = ""
#             else:
#                 cur += ch
#         if cur.strip():
#             inner.append(cur.strip())
#         return make_const(m.group(1), *[parse_term(a) for a in inner])
    
#     # 数字
#     if t.isdigit():
#         return make_const(t)
    
#     # 单字母（大小写）→ 变量
#     if re.match(r'^[a-zA-Z]$', t):
#         return make_var(t)
    
#     # 其他 → 常量
#     return make_const(t)


# ★ 方案 A：默认只把这些字母当 Var，其余单字母一律当 Const
DEFAULT_VAR_NAMES = tuple('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ') + ('n', 'k', 'x', 'y', 'z', 'S', 'N', 'K')


def parse_term(t: str, var_names: Tuple[str, ...] = DEFAULT_VAR_NAMES):
    t = t.strip()
    # 嵌套函数/常量：name(args...)
    m = re.match(r'(\w+)\((.+)\)', t)
    if m:
        inner = []
        depth = 0
        cur = ""
        for ch in m.group(2):
            if ch == '(':
                depth += 1; cur += ch
            elif ch == ')':
                depth -= 1; cur += ch
            elif ch == ',' and depth == 0:
                inner.append(cur.strip()); cur = ""
            else:
                cur += ch
        if cur.strip():
            inner.append(cur.strip())
        return make_const(m.group(1), *[parse_term(a, var_names) for a in inner])

    # 数字
    if t.isdigit():
        return make_const(t)

    # ★ 单字母：只有列在 var_names 里的才当 Var，其余当 Const
    if re.match(r'^[a-zA-Z]$', t):
        if t in var_names:
            return make_var(t)
        return make_const(t)

    # 其他 → 常量
    return make_const(t)


def parse_goal(s: str,
               var_names: Tuple[str, ...] = DEFAULT_VAR_NAMES) -> Optional[Pred]:
    s = s.strip()
    if re.match(r'^\w+$', s):
        return make_pred(s)
    m = re.match(r'(\w+)\((.+)\)', s)
    if not m:
        return None
    args = []
    depth = 0
    cur = ""
    for ch in m.group(2):
        if ch == '(':
            depth += 1; cur += ch
        elif ch == ')':
            depth -= 1; cur += ch
        elif ch == ',' and depth == 0:
            args.append(cur.strip()); cur = ""
        else:
            cur += ch
    if cur.strip():
        args.append(cur.strip())
    return make_pred(m.group(1),
                     *[parse_term(a, var_names) for a in args])


# ============================================================
# 八、CLI
# ============================================================

def cli():
    parser = argparse.ArgumentParser(description="数论定理自动证明 v3")
    parser.add_argument('--prove', type=str, help='证明目标')
    parser.add_argument('--strategy',
                        choices=['auto', 'direct', 'contradiction', 'induction'],
                        default='auto')
    parser.add_argument('--var', type=str, default=None)
    parser.add_argument('--base', type=str, default='1')
    parser.add_argument('--max_depth', type=int, default=12)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--premise', type=str, action='append', default=[],
                help='前提条件（可以多个，每个 --premise 一个）')
    args = parser.parse_args()


    # 用 AdaptiveStore 加载
    from adaptive_store import AdaptiveStore
    store = AdaptiveStore()
    # 硬编码定理
    for c in build_theorem_db():
        store.add(c)
    # JSONL 定理
    import glob as _glob
    for _path in sorted(_glob.glob('theorems/*.jsonl')):
        if os.path.exists(_path):
            store.load_jsonl(_path)
    print(f"[cli] 加载了 {len(store.clauses)} 条定理")
    
    if args.prove:
        prover = Prover(store, max_depth=args.max_depth)

        goal = parse_goal(args.prove)
        
        #print(f"[cli] goal={goal}")
        #print(f"[cli] goal.args={goal.args}")
        for a in goal.args:
            print(f"[cli] a={a}, type={type(a).__name__}")
        
        if goal is None:
            print(f"无法解析: {args.prove}")
            return
        var = Var(args.var) if args.var else None
        
        if args.premise:
            premises = [parse_goal(p) for p in args.premise]
            premises = [p for p in premises if p is not None]
            proof = prover.prove_with_premises(
                goal, premises, strategy=args.strategy, var=var, verbose=True
            )
        else:
            proof = prover.prove(goal, strategy=args.strategy, var=var, verbose=True)

        print_proof(proof, goal)
        return
        
        proof = prover.prove(goal, strategy=args.strategy, var=var,
                             base_value=args.base, verbose=True)
        print_proof(proof, goal)
        return

    if args.demo:
        prover = Prover(store, max_depth=args.max_depth)
        tests = [
            ("prime(3)", "direct", None),
            ("prime_infinite", "contradiction", None),
            ("sum_to_n(1, 1)", "direct", None),
            ("sum_to_n(k, S)", "induction", Var("k")),
        ]
        for g, strat, var in tests:
            goal = parse_goal(g)
            print(f"\n{'='*60}")
            print(f"测试: {g}  策略: {strat}")
            proof = prover.prove(goal, strategy=strat, var=var, verbose=True)
            print_proof(proof, goal)
        return

    parser.print_help()


if __name__ == "__main__":
    cli()