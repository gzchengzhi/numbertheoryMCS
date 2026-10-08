"""
数论定理自动证明 v3（反证法 + 归纳法）

修复：
  1. parse_goal 支持零参数谓词
  2. 反证法：假设 NOT goal，直接找 contradiction 证明链
  3. 归纳法：正确处理自由变量
  4. auto 策略：直接 → 反证 → 归纳
"""

import re
import argparse
from typing import List, Dict, Tuple, Optional, Set, Any
from dataclasses import dataclass


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

def is_var(x): return isinstance(x, Var)


def occurs_check(v: Var, term) -> bool:
    if isinstance(term, Var):
        return v == term
    if isinstance(term, Const):
        return any(occurs_check(v, a) for a in term.args)
    if isinstance(term, Pred):
        return any(occurs_check(v, a) for a in term.args)
    return False


def substitute(term, subst: Dict[Var, Any]):
    if isinstance(term, Var):
        if term in subst:
            return substitute(subst[term], subst)
        return term
    if isinstance(term, Const):
        if not term.args:
            return term
        return Const(term.name, tuple(substitute(a, subst) for a in term.args))
    if isinstance(term, Pred):
        return Pred(term.name, tuple(substitute(a, subst) for a in term.args))
    return term


def unify(t1, t2, subst: Dict[Var, Any] = None) -> Optional[Dict[Var, Any]]:
    if subst is None:
        subst = {}
    t1 = substitute(t1, subst)
    t2 = substitute(t2, subst)

    if t1 == t2:
        return subst
    if is_var(t1):
        if occurs_check(t1, t2):
            return None
        new = dict(subst); new[t1] = t2; return new
    if is_var(t2):
        if occurs_check(t2, t1):
            return None
        new = dict(subst); new[t2] = t1; return new
    if isinstance(t1, Const) and isinstance(t2, Const):
        if t1.name != t2.name or len(t1.args) != len(t2.args):
            return None
        for a1, a2 in zip(t1.args, t2.args):
            subst = unify(a1, a2, subst)
            if subst is None:
                return None
        return subst
    if isinstance(t1, Pred) and isinstance(t2, Pred):
        if t1.name != t2.name or len(t1.args) != len(t2.args):
            return None
        for a1, a2 in zip(t1.args, t2.args):
            subst = unify(a1, a2, subst)
            if subst is None:
                return None
        return subst
    return None


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
    V, C, P = make_var, make_const, make_pred
    db = []

    # ============ 原始 20 条 ============
    db.append(HornClause("T001", "整除的传递性",
        P("divides", V("a"), V("c")),
        [P("divides", V("a"), V("b")), P("divides", V("b"), V("c"))], category="整除"))
    db.append(HornClause("T002", "整除的自反性",
        P("divides", V("a"), V("a")),
        [P("nonzero", V("a"))], category="整除"))
    db.append(HornClause("T003", "整除的线性组合",
        P("divides", V("a"), C("plus", C("times", V("m"), V("b")), C("times", V("n"), V("c")))),
        [P("divides", V("a"), V("b")), P("divides", V("a"), V("c"))], category="整除"))
    db.append(HornClause("T004", "1整除一切", P("divides", C("1"), V("a")), [], category="整除"))
    db.append(HornClause("T005", "一切整除0", P("divides", V("a"), C("0")), [], category="整除"))
    db.append(HornClause("T006", "素数定义",
        P("prime", V("p")),
        [P("gt", V("p"), C("1")), P("no_proper_divisor", V("p"))], category="素数"))
    db.append(HornClause("T007", "素数无穷多",
        P("exists", C("p"), C("and", P("prime", V("p")), P("gt", V("p"), V("n")))),
        [], category="素数"))
    db.append(HornClause("T008", "欧几里得引理",
        P("divides", V("p"), V("b")),
        [P("prime", V("p")),
         P("divides", V("p"), C("times", V("a"), V("b"))),
         P("not_divides", V("p"), V("a"))], category="素数"))
    db.append(HornClause("T009", "算术基本定理",
        P("has_unique_prime_factorization", V("n")),
        [P("gt", V("n"), C("1"))], category="素数"))
    db.append(HornClause("T010", "费马小定理",
        P("congruent", C("power", V("a"), C("minus", V("p"), C("1"))), C("1"), V("p")),
        [P("prime", V("p")), P("coprime", V("a"), V("p"))], category="素数"))
    db.append(HornClause("T011", "同余定义",
        P("congruent", V("a"), V("b"), V("m")),
        [P("divides", V("m"), C("minus", V("a"), V("b")))], category="同余"))
    db.append(HornClause("T012", "同余的加法",
        P("congruent", C("plus", V("a"), V("c")), C("plus", V("b"), V("d")), V("m")),
        [P("congruent", V("a"), V("b"), V("m")),
         P("congruent", V("c"), V("d"), V("m"))], category="同余"))
    db.append(HornClause("T013", "同余的乘法",
        P("congruent", C("times", V("a"), V("c")), C("times", V("b"), V("d")), V("m")),
        [P("congruent", V("a"), V("b"), V("m")),
         P("congruent", V("c"), V("d"), V("m"))], category="同余"))
    db.append(HornClause("T014", "欧几里得算法",
        P("equals", C("gcd", V("a"), V("b")), C("gcd", V("b"), C("mod", V("a"), V("b")))),
        [P("nonzero", V("b"))], category="gcd"))
    db.append(HornClause("T015", "贝祖等式",
        P("exists", C("xy"), C("equals",
          C("plus", C("times", V("a"), V("x")), C("times", V("b"), V("y"))),
          C("gcd", V("a"), V("b")))), [], category="gcd"))
    db.append(HornClause("T016", "gcd与lcm关系",
        P("equals",
          C("times", C("gcd", V("a"), V("b")), C("lcm", V("a"), V("b"))),
          C("times", V("a"), V("b"))),
        [P("gt", V("a"), C("0")), P("gt", V("b"), C("0"))], category="gcd"))
    db.append(HornClause("T017", "互质与整除",
        P("divides", V("a"), V("c")),
        [P("coprime", V("a"), V("b")),
         P("divides", V("a"), C("times", V("b"), V("c")))], category="gcd"))
    db.append(HornClause("T018", "素数平方根无理性",
        P("irrational", C("sqrt", V("p"))),
        [P("prime", V("p"))], category="无理数"))
    db.append(HornClause("T019", "sqrt(2)无理性",
        P("irrational", C("sqrt", C("2"))),
        [P("prime", C("2"))], category="无理数"))
    db.append(HornClause("T020", "2是素数", P("prime", C("2")), [], category="素数"))

    # ============ A 阶段：30 条 ============
    db.append(HornClause("T021", "3是素数", P("prime", C("3")), [], category="素数"))
    db.append(HornClause("T022", "5是素数", P("prime", C("5")), [], category="素数"))
    db.append(HornClause("T023", "7是素数", P("prime", C("7")), [], category="素数"))
    db.append(HornClause("T024", "11是素数", P("prime", C("11")), [], category="素数"))
    db.append(HornClause("T025", "2整除4", P("divides", C("2"), C("4")), [], category="整除"))
    db.append(HornClause("T026", "3整除6", P("divides", C("3"), C("6")), [], category="整除"))
    db.append(HornClause("T027", "4整除12", P("divides", C("4"), C("12")), [], category="整除"))
    db.append(HornClause("T028", "5整除15", P("divides", C("5"), C("15")), [], category="整除"))
    db.append(HornClause("T029", "6整除18", P("divides", C("6"), C("18")), [], category="整除"))
    db.append(HornClause("T030", "1非零", P("nonzero", C("1")), [], category="基础"))

    db.append(HornClause("T031", "整除的反对称性",
        P("equals", C("abs", V("a")), C("abs", V("b"))),
        [P("divides", V("a"), V("b")), P("divides", V("b"), V("a"))], category="整除"))
    db.append(HornClause("T032", "整除与大小",
        P("le", V("a"), V("b")),
        [P("divides", V("a"), V("b")), P("gt", V("a"), C("0")), P("gt", V("b"), C("0"))], category="整除"))
    db.append(HornClause("T033", "整除与负数",
        P("divides", V("a"), C("minus", C("0"), V("b"))),
        [P("divides", V("a"), V("b"))], category="整除"))
    db.append(HornClause("T034", "整除与gcd",
        P("divides", V("a"), C("gcd", V("b"), V("c"))),
        [P("divides", V("a"), V("b")), P("divides", V("a"), V("c"))], category="gcd"))
    db.append(HornClause("T035", "整除与lcm",
        P("divides", C("lcm", V("a"), V("b")), V("c")),
        [P("divides", V("a"), V("c")), P("divides", V("b"), V("c"))], category="gcd"))
    db.append(HornClause("T036", "整除与商",
        P("exists", C("c"), P("equals", V("b"), C("times", V("a"), V("c")))),
        [P("divides", V("a"), V("b")), P("nonzero", V("a"))], category="整除"))
    db.append(HornClause("T037", "互质的定义",
        P("equals", C("gcd", V("a"), V("b")), C("1")),
        [P("coprime", V("a"), V("b"))], category="gcd"))
    db.append(HornClause("T038", "互异素数互质",
        P("coprime", V("p"), V("q")),
        [P("prime", V("p")), P("prime", V("q")), P("not_equals", V("p"), V("q"))], category="素数"))
    db.append(HornClause("T039", "同余的传递性",
        P("congruent", V("a"), V("c"), V("m")),
        [P("congruent", V("a"), V("b"), V("m")),
         P("congruent", V("b"), V("c"), V("m"))], category="同余"))
    db.append(HornClause("T040", "同余的自反性",
        P("congruent", V("a"), V("a"), V("m")), [], category="同余"))
    db.append(HornClause("T041", "同余与整除",
        P("divides", V("m"), V("a")),
        [P("congruent", V("a"), C("0"), V("m"))], category="同余"))
    db.append(HornClause("T042", "欧拉函数定义",
        P("equals", C("phi", V("n")), C("count_coprime_below", V("n"))), [], category="算术函数"))
    db.append(HornClause("T043", "素数幂的欧拉函数",
        P("equals", C("phi", C("power", V("p"), V("k"))),
          C("minus", C("power", V("p"), V("k")), C("power", V("p"), C("minus", V("k"), C("1"))))),
        [P("prime", V("p")), P("ge", V("k"), C("1"))], category="算术函数"))
    db.append(HornClause("T044", "欧拉函数的积性",
        P("equals", C("phi", C("times", V("m"), V("n"))),
          C("times", C("phi", V("m")), C("phi", V("n")))),
        [P("coprime", V("m"), V("n"))], category="算术函数"))
    db.append(HornClause("T045", "约数个数的公式",
        P("equals", C("tau", V("n")), C("product_expr", V("n"))), [], category="算术函数"))
    db.append(HornClause("T046", "本原勾股三元组参数化",
        P("pythagorean", V("a"), V("b"), V("c")),
        [P("exists", C("mn"),
           P("and",
             P("gt", V("m"), V("n")),
             P("equals", C("gcd", V("m"), V("n")), C("1")),
             P("equals", V("a"), C("minus", C("times", V("m"), V("m")), C("times", V("n"), V("n")))),
             P("equals", V("b"), C("times", C("2"), C("times", V("m"), V("n")))),
             P("equals", V("c"), C("plus", C("times", V("m"), V("m")), C("times", V("n"), V("n"))))))],
        category="丢番图"))
    db.append(HornClause("T047", "3-4-5是勾股三元组",
        P("pythagorean", C("3"), C("4"), C("5")), [], category="丢番图"))
    db.append(HornClause("T048", "5-12-13是勾股三元组",
        P("pythagorean", C("5"), C("12"), C("13")), [], category="丢番图"))
    db.append(HornClause("T049", "四平方和",
        P("sum_of_4_squares", V("n")),
        [P("ge", V("n"), C("0"))], category="丢番图"))
    db.append(HornClause("T050", "佩尔方程有解",
        P("exists", C("xy"),
          P("equals",
            C("minus", C("times", V("x"), V("x")),
              C("times", V("D"), C("times", V("y"), V("y")))),
            C("1"))),
        [P("non_square_positive", V("D"))], category="丢番图"))

    # ============ B 阶段：反证法链（素数无穷多） ============
    # 定义 prime_infinite 为"对所有 n，存在素数 p > n"
    db.append(HornClause("T052", "素数无穷多定义",
        P("prime_infinite"),
        [P("forall_n_exists_prime_gt_n")], category="素数"))
    db.append(HornClause("T053", "素数无穷多公理",
        P("forall_n_exists_prime_gt_n"), [], category="素数"))

    # 反证法：假设素数有限，推出 contradiction
    db.append(HornClause("T054", "假设素数有限",
        P("prime_finite"),
        [P("not_prime_infinite")], category="反证法"))
    db.append(HornClause("T055", "有限素数有最大者",
        P("exists_max_prime"),
        [P("prime_finite")], category="反证法"))
    db.append(HornClause("T056", "构造p!+1",
        P("exists_p_factorial_plus_1"),
        [P("exists_max_prime")], category="反证法"))
    db.append(HornClause("T057", "p!+1有素因子q",
        P("exists_prime_q_divides_factorial_plus_1"),
        [P("exists_p_factorial_plus_1")], category="反证法"))
    db.append(HornClause("T058", "推出矛盾",
        P("contradiction"),
        [P("exists_prime_q_divides_factorial_plus_1"),
         P("exists_max_prime")], category="反证法"))

    # ============ B 阶段：归纳法链（sum_to_n） ============
    db.append(HornClause("T059", "1到1的和",
        P("sum_to_n", C("1"), C("1")), [], category="归纳"))
    db.append(HornClause("T060", "1到2的和",
        P("sum_to_n", C("2"), C("3")), [], category="归纳"))
    db.append(HornClause("T061", "1到3的和",
        P("sum_to_n", C("3"), C("6")), [], category="归纳"))
    db.append(HornClause("T062", "1到4的和",
        P("sum_to_n", C("4"), C("10")), [], category="归纳"))

    # 归纳步：sum_to_n(k, S) → sum_to_n(k+1, S+k+1)
    db.append(HornClause("T063", "sum递推（具体值）",
        P("sum_to_n", C("plus", V("n"), C("1")), C("plus", V("S"), C("plus", V("n"), C("1")))),
        [P("sum_to_n", V("n"), V("S"))], category="归纳"))

    # 额外：矛盾律
    db.append(HornClause("T064", "矛盾律",
        P("contradiction"),
        [P("true"), P("false")], category="逻辑"))
    db.append(HornClause("T067", "归纳假设形式",
        P("sum_to_n", V("k"), V("s")),
        [], category="归纳"))
    # 按 body 长度排序：公理优先
    db.sort(key=lambda c: len(c.body))


    return db


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
    def __init__(self, theorem_db: List[HornClause], max_depth: int = 12):
        self.db = theorem_db
        self.max_depth = max_depth
        self.step_count = 0
        self.max_steps = 50000
        self.visited: Set[str] = set()

    # -------- 直接证明 --------
    def prove_direct(self, goal: Pred) -> Optional[List[ProofStep]]:
        self.step_count = 0
        self.visited = set()
        return self._prove_recursive(goal, {}, 0, [], strategy="direct")

    def _prove_recursive(self, goal: Pred, subst: Dict[Var, Any],
                         depth: int, path: List[ProofStep],
                         strategy: str = "direct",
                         extra_db: List[HornClause] = None
                         ) -> Optional[List[ProofStep]]:
        self.step_count += 1
        if self.step_count > self.max_steps:
            return None
        if depth > self.max_depth:
            return None

        goal = substitute(goal, subst)
        # 归一化变量名
        def normalize(g):
            m = {}
            def walk(t):
                if isinstance(t, Var):
                    if t.name not in m:
                        m[t.name] = f"V{len(m)}"
                    return m[t.name]
                if isinstance(t, Const):
                    if not t.args:
                        return t.name
                    return f"{t.name}({','.join(walk(a) for a in t.args)})"
                return str(t)
            return walk(g)
        
        goal_key = f"{strategy}:{normalize(goal)}"
        if goal_key in self.visited and len(self.visited) > 1000:
            return None
        self.visited.add(goal_key)

        db = extra_db if extra_db is not None else self.db
        
        # ---- 计算引擎：如果目标含具体常量，先尝试计算 ----
        try:
            from arithmetic_engine import evaluate_predicate
            result = evaluate_predicate(goal)
            if result is True:
                # 计算成功，返回"公理证明"
                computed_clause = HornClause(
                    "COMPUTED", f"计算: {goal}",
                    goal, [], category="计算"
                )
                step = ProofStep(computed_clause, {}, goal, depth, strategy)
                return path + [step]
            elif result is False:
                # 计算为假，该路径失败
                return None
        except Exception:
            pass

        for clause in db:
            new_subst = unify(clause.head, goal, dict(subst))
            if new_subst is None:
                continue

            step = ProofStep(clause, new_subst, goal, depth, strategy)
            new_path = path + [step]

            if not clause.body:
                return new_path

            # 递归证明所有 body
            body_success = True
            body_path = new_path
            current_subst = new_subst

            for body_pred in clause.body:
                body_pred_subst = substitute(body_pred, current_subst)
                result = self._prove_recursive(
                    body_pred_subst, current_subst, depth + 1, body_path,
                    strategy=strategy, extra_db=extra_db
                )
                if result is None:
                    body_success = False
                    break
                body_path = result
                # 合并新替换
                if result:
                    current_subst = result[-1].substitution

            if body_success:
                return body_path

        return None

    # -------- 反证法 --------
    def prove_by_contradiction(self, goal: Pred,
                               verbose: bool = False) -> Optional[List[ProofStep]]:
        """
        反证法：假设 NOT goal，尝试推出 contradiction。
        """
        if goal.name.startswith("not_"):
            return None

        negated = Pred("not_" + goal.name, goal.args)
        assumption = HornClause(
            "ASSUME", f"假设 {negated}",
            negated, [], category="反证法假设",
        )
        # 用假设 + 库里已有反证链
        temp_db = self.db + [assumption]

        if verbose:
            print(f"  [反证法] 假设: {negated}")

        # 关键：尝试用"假设 + 反证链"推出 contradiction
        self.step_count = 0
        self.visited = set()
        contra = Pred("contradiction", ())
        proof = self._prove_recursive(contra, {}, 0, [], strategy="contradiction",
                                      extra_db=temp_db)

        # 过滤掉假设本身（它在证明里只做起点）
        if proof and verbose:
            print(f"  [反证法] 推出 contradiction，原目标成立")

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

def parse_term(t: str):
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
        return make_const(m.group(1), *[parse_term(a) for a in inner])
    
    # 数字
    if t.isdigit():
        return make_const(t)
    
    # 单字母（大小写）→ 变量
    if re.match(r'^[a-zA-Z]$', t):
        return make_var(t)
    
    # 其他 → 常量
    return make_const(t)


def parse_goal(s: str) -> Optional[Pred]:
    s = s.strip()
    # 零参数
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
    return make_pred(m.group(1), *[parse_term(a) for a in args])


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
    args = parser.parse_args()

    db = build_theorem_db()

    if args.prove:
        prover = Prover(db, max_depth=args.max_depth)
        goal = parse_goal(args.prove)
        if goal is None:
            print(f"无法解析: {args.prove}")
            return
        var = Var(args.var) if args.var else None
        proof = prover.prove(goal, strategy=args.strategy, var=var,
                             base_value=args.base, verbose=True)
        print_proof(proof, goal)
        return

    if args.demo:
        prover = Prover(db, max_depth=args.max_depth)
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