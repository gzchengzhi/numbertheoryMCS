# -*- coding: utf-8 -*-
"""
符号化简与等价判断（sympy 驱动）

独立模块，不依赖 numtheory_prover 的除 Var/Const/Pred 之外的部分。
所有对 numtheory_prover 的 import 都在函数内延迟执行，避免循环依赖。
"""

import sympy as sp
from functools import lru_cache
from typing import Optional

# ============================================================
# 类型工具（对 reload 免疫）
# ============================================================

def _get_classes():
    from numtheory_prover import Var, Const, Pred
    return Var, Const, Pred


def _type_name(term) -> str:
    return type(term).__name__


# ============================================================
# 项 ↔ sympy 表达式
# ============================================================

_SYMPY_FUNC_MAP = {
    "plus":  lambda *a: sp.Add(*a),
    "minus": lambda a, b: a - b,
    "times": lambda *a: sp.Mul(*a),
    "div":   lambda a, b: a / b,
    "mod":   lambda a, b: sp.Mod(a, b),
    "power": lambda a, b: a ** b,
    "abs":   lambda a: sp.Abs(a),
    "gcd":   lambda a, b: sp.gcd(a, b),
    "lcm":   lambda a, b: sp.lcm(a, b),
    "factorial": lambda a: sp.factorial(a),
    "sqrt":  lambda a: sp.sqrt(a),
    "phi":   lambda a: sp.totient(a),
    "tau":   lambda a: sp.divisor_count(a),
    "sigma": lambda a: sp.divisor_sigma(a),
}


def term_to_sympy(term, var_map: dict):
    """把系统里的项转成 sympy 表达式"""
    tname = _type_name(term)

    if tname == 'Var':
        if term.name not in var_map:
            var_map[term.name] = sp.Symbol(term.name, integer=True)
        return var_map[term.name]
    
    if tname == 'Const' and term.name == "sum" and len(term.args) == 4:
        var = term.args[0]
        lower = term.args[1]
        upper = term.args[2]
        body = term.args[3]
        i_sym = sp.Symbol(var.name, integer=True)
        var_map[var.name] = i_sym
        lo = term_to_sympy(lower, var_map)
        up = term_to_sympy(upper, var_map)
        body_sym = term_to_sympy(body, var_map)
        return sp.Sum(body_sym, (i_sym, lo, up))

    if tname in ('Const', 'Pred'):
        if not term.args:
            try:
                return sp.Integer(int(term.name))
            except ValueError:
                return sp.Symbol(term.name)
        args = [term_to_sympy(a, var_map) for a in term.args]
        fn = _SYMPY_FUNC_MAP.get(term.name)
        if fn is None:
            return sp.Function(term.name)(*args)
        return fn(*args)

    if isinstance(term, (int, float)):
        return sp.Integer(term)

    if isinstance(term, str):
        try:
            return sp.Integer(int(term))
        except ValueError:
            return sp.Symbol(term)

    raise ValueError(f"无法转 sympy: {term} (类型 {tname})")


def sympy_to_term(expr, var_map_inv):
    """把 sympy 表达式转回系统的项"""
    Var, Const, Pred = _get_classes()

    if isinstance(expr, sp.Symbol):
        name = str(expr)
        if name in var_map_inv:
            return var_map_inv[name]
        return Const(name)

    if isinstance(expr, sp.Integer):
        return Const(str(expr))

    if isinstance(expr, sp.Rational):
        return Const("div", (Const(str(expr.p)), Const(str(expr.q))))

    if isinstance(expr, sp.Add):
        terms = list(expr.args)
        def key(t):
            if not t.free_symbols:   # ← 快，不用 is_constant()
                return (1, 0)
            return (0, -sp.total_degree(t))
        terms.sort(key=key)
        args = [sympy_to_term(t, var_map_inv) for t in terms]
        result = args[-1]
        for a in reversed(args[:-1]):
            result = Const("plus", (a, result))
        return result

    if isinstance(expr, sp.Mul):
        coeff, rest = expr.as_coeff_Mul()
        
        # ★ 特殊处理：coeff = 1/2 → div(rest, 2)
        if coeff == sp.Rational(1, 2):
            rest_term = sympy_to_term(rest, var_map_inv)
            return Const("div", (rest_term, Const("2")))

        if coeff == -1:
            return Const("minus", (Const("0"),
                                   sympy_to_term(rest, var_map_inv)))
        if coeff != 1:
            rest_term = sympy_to_term(rest, var_map_inv)
            return Const("times", (Const(str(coeff)), rest_term))
        args = [sympy_to_term(a, var_map_inv) for a in expr.args]
        result = args[0]
        for a in args[1:]:
            result = Const("times", (result, a))
        return result

    if isinstance(expr, sp.Pow):
        base = sympy_to_term(expr.base, var_map_inv)
        exp = sympy_to_term(expr.exp, var_map_inv)
        return Const("power", (base, exp))

    if isinstance(expr, sp.Mod):
        return Const("mod", (sympy_to_term(expr.args[0], var_map_inv),
                             sympy_to_term(expr.args[1], var_map_inv)))

    if isinstance(expr, sp.Abs):
        return Const("abs", (sympy_to_term(expr.args[0], var_map_inv),))

    if isinstance(expr, sp.Function):
        name = expr.func.__name__
        args = [sympy_to_term(a, var_map_inv) for a in expr.args]
        return Const(name, tuple(args))

    return Const(str(expr))


# ============================================================
# 化简
# ============================================================

def simplify_term(term, mode: str = "full"):
    """
    对单个项做符号化简。
    mode: "factor" / "expand" / "full" / "trig"
    """
    # 1. 收集项里的 Var 实例（name -> Var）
    var_instances = {}

    def _collect_vars(t):
        tn = _type_name(t)
        if tn == 'Var':
            var_instances[t.name] = t
        elif tn in ('Const', 'Pred'):
            for a in t.args:
                _collect_vars(a)

    _collect_vars(term)

    # 2. 转 sympy
    var_map = {}
    try:
        expr = term_to_sympy(term, var_map)
    except Exception:
        return term

    # ★ 含 factorial 的表达式跳过化简（sympy 对 factorial 极慢且不可靠）
    if expr.has(sp.factorial):
        return term

    # 3. 化简
    try:
        if mode == "factor":
            simplified = sp.factor(expr)
        elif mode == "expand":
            simplified = sp.expand(expr)
        elif mode == "trig":
            simplified = sp.trigsimp(expr)
        else:  # full
            simplified = sp.factor(sp.expand(expr))
            if simplified == sp.expand(expr):
                simplified = sp.trigsimp(simplified)
    except Exception:
        return term

    # 4. 构造 var_map_inv：sympy.Symbol 名 -> Var 实例
    var_map_inv = {}
    for name, sym in var_map.items():
        if name in var_instances:
            var_map_inv[str(sym)] = var_instances[name]

    # 5. 转回系统的项
    try:
        return sympy_to_term(simplified, var_map_inv)
    except Exception:
        return term


def _simplify_nested(term):
    """递归化简项"""
    Var, Const, Pred = _get_classes()
    tname = _type_name(term)

    if tname == 'Var':
        return term

    if tname == 'Const':
        if not term.args:
            return term
        new_args = tuple(_simplify_nested(a) for a in term.args)
        new_term = Const(term.name, new_args)
        return simplify_term(new_term, mode="full")

    return term


def simplify_predicate(pred):
    """
    对谓词的每个参数做符号化简。
    返回化简后的谓词；若化简后与原来等价，返回原谓词。
    """
    
    # 如果 pred 含 sum，跳过化简
    if _contains_sum(pred):
        return pred
    
    Var, Const, Pred = _get_classes()
    tname = _type_name(pred)

    if tname == 'Var':
        return pred
    if tname != 'Pred':
        return pred

    new_args = []
    changed = False
    for a in pred.args:
        new_a = _simplify_nested(a)
        if new_a != a:
            changed = True
        new_args.append(new_a)

    if not changed:
        return pred
    return Pred(pred.name, tuple(new_args))

def _contains_sum(term):
    tn = _type_name(term)
    if tn == 'Const' and term.name == "sum":
        return True
    if tn in ('Const', 'Pred'):
        return any(_contains_sum(a) for a in term.args)
    return False


# ============================================================
# 数学等价判断
# ============================================================

@lru_cache(maxsize=100000)
def _math_equivalent_cached(t1, t2) -> bool:
    var_map = {}
    try:
        e1 = term_to_sympy(t1, var_map)
        e2 = term_to_sympy(t2, var_map)
        # ★ 含 factorial 的跳过（sympy 对 factorial 极慢且不可靠）
        if e1.has(sp.factorial) or e2.has(sp.factorial):
            return False
        diff = sp.simplify(e1 - e2)
        return diff == 0
    except Exception:
        return False


def math_equivalent(t1, t2) -> bool:
    """判断两个项是否数学等价（带缓存）"""
    try:
        return _math_equivalent_cached(t1, t2)
    except TypeError:
        # 不可 hash，退化为非缓存
        var_map = {}
        try:
            e1 = term_to_sympy(t1, var_map)
            e2 = term_to_sympy(t2, var_map)
            return sp.simplify(e1 - e2) == 0
        except Exception:
            return False
        
# ============================================================
# 变量约束
# ============================================================

def collect_constraints(extra_db, var_name: str, visited=None) -> dict:
    """
    从 extra_db 里递归收集关于 var_name 的约束。
    返回 {var_name: {'lower': [(val, inclusive), ...],
                     'upper': [(val, inclusive), ...],
                     'ne':    [val, ...],
                     'eq':    [val, ...]}}
    """
    if visited is None:
        visited = set()
    if var_name in visited:
        return {}
    visited.add(var_name)

    result = {'lower': [], 'upper': [], 'ne': [], 'eq': []}

    if extra_db is None:
        return result

    for clause in extra_db:
        # 只处理单变量约束：head 是 gt/ge/lt/le/ne/equals，body 可以为空或非空
        if _type_name(clause.head) != 'Pred':
            continue
        name = clause.head.name
        if name not in ("gt", "ge", "lt", "le", "ne", "equals"):
            continue
        if len(clause.head.args) != 2:
            continue

        # 检查第一个参数是否是 var_name
        a1, a2 = clause.head.args
        if _type_name(a1) != 'Var' or a1.name != var_name:
            continue

        # 第二个参数必须是常量或数值
        if _type_name(a2) == 'Var':
            continue

        # 提取约束
        if name == "ge":
            result['lower'].append((a2, True))
        elif name == "gt":
            result['lower'].append((a2, False))
        elif name == "le":
            result['upper'].append((a2, True))
        elif name == "lt":
            result['upper'].append((a2, False))
        elif name == "ne":
            result['ne'].append(a2)
        elif name == "equals":
            result['eq'].append(a2)

        # 递归：如果 clause 有 body，收集 body 里关于 var_name 的约束
        if clause.body:
            for b in clause.body:
                if _type_name(b) != 'Pred':
                    continue
                if b.name in ("gt", "ge", "lt", "le", "ne", "equals") and len(b.args) == 2:
                    b1, b2 = b.args
                    if _type_name(b1) == 'Var' and b1.name == var_name:
                        if _type_name(b2) != 'Var':
                            if b.name == "ge":
                                result['lower'].append((b2, True))
                            elif b.name == "gt":
                                result['lower'].append((b2, False))
                            elif b.name == "le":
                                result['upper'].append((b2, True))
                            elif b.name == "lt":
                                result['upper'].append((b2, False))
                            elif b.name == "ne":
                                result['ne'].append(b2)
                            elif b.name == "equals":
                                result['eq'].append(b2)

    return result


def merge_constraints(constraints: dict) -> tuple:
    """
    合并约束，返回 (lower, lower_inclusive, upper, upper_inclusive, ne_list, eq_list)
    lower/upper 为 None 表示无界。
    """
    lower = None
    lower_incl = True
    upper = None
    upper_incl = True
    ne_list = list(constraints.get('ne', []))
    eq_list = list(constraints.get('eq', []))

    for val, incl in constraints.get('lower', []):
        if lower is None:
            lower, lower_incl = val, incl
        else:
            # 取更紧的下界
            try:
                v1 = float(val.name) if _type_name(val) == 'Const' else None
                v2 = float(lower.name) if _type_name(lower) == 'Const' else None
                if v1 is None or v2 is None:
                    continue
                if v1 > v2:
                    lower, lower_incl = val, incl
                elif v1 == v2 and not incl:
                    lower_incl = False
            except Exception:
                continue

    for val, incl in constraints.get('upper', []):
        if upper is None:
            upper, upper_incl = val, incl
        else:
            try:
                v1 = float(val.name) if _type_name(val) == 'Const' else None
                v2 = float(upper.name) if _type_name(upper) == 'Const' else None
                if v1 is None or v2 is None:
                    continue
                if v1 < v2:
                    upper, upper_incl = val, incl
                elif v1 == v2 and not incl:
                    upper_incl = False
            except Exception:
                continue

    return lower, lower_incl, upper, upper_incl, ne_list, eq_list


# ============================================================
# 符号不等式证明
# ============================================================

def _min_on_constraints(expr, var, lower, upper):
    """
    求 expr 在 var ∈ [lower, upper] 上的最小值。
    lower/upper 为 None 表示无界。
    """
    try:
        candidates = []
        if lower is not None:
            candidates.append(lower)
        if upper is not None:
            candidates.append(upper)

        # 求导找驻点
        d = sp.diff(expr, var)
        critical = sp.solve(d, var)
        for c in critical:
            if c.is_real:
                if lower is not None and c < lower:
                    continue
                if upper is not None and c > upper:
                    continue
                candidates.append(c)

        if not candidates:
            return None

        values = []
        for c in candidates:
            try:
                values.append(expr.subs(var, c))
            except Exception:
                continue
        if not values:
            return None
        return min(values)
    except Exception:
        return None


def prove_inequality_symbolic(pred, constraints: dict) -> Optional[bool]:
    """
    证明形如 gt/ge/lt/le/ne 的不等式。
    constraints: {var_name: {'lower': [...], 'upper': [...], 'ne': [...], 'eq': [...]}}
    返回 True / False / None
    """
    tname = _type_name(pred)
    if tname != 'Pred':
        return None
    if pred.name not in ("gt", "ge", "lt", "le", "ne"):
        return None
    if len(pred.args) != 2:
        return None

    f, g = pred.args
    # 收集 f 和 g 里的变量
    var_names = _collect_var_names(f) | _collect_var_names(g)
    if len(var_names) != 1:
        return None  # 多变量暂不支持
    var_name = list(var_names)[0]

    # 提取约束
    cons = constraints.get(var_name, {})
    lower_t, lower_incl, upper_t, upper_incl, ne_list, eq_list = merge_constraints(cons)

    # 转 sympy
    var_map = {}
    try:
        fe = term_to_sympy(f, var_map)
        ge_ = term_to_sympy(g, var_map)
    except Exception:
        return None

    v = var_map.get(var_name)
    if v is None:
        return None

    def _to_float(t):
        if t is None:
            return None
        try:
            return float(t.name) if _type_name(t) == 'Const' else float(t)
        except Exception:
            return None

    lo = _to_float(lower_t)
    up = _to_float(upper_t)

    try:
        if pred.name == "gt":
            expr = sp.expand(fe - ge_)
            min_val = _min_on_constraints(expr, v, lo, up)
            if min_val is None:
                return None
            return bool(min_val > 0)

        if pred.name == "ge":
            expr = sp.expand(fe - ge_)
            min_val = _min_on_constraints(expr, v, lo, up)
            if min_val is None:
                return None
            return bool(min_val >= 0)

        if pred.name == "lt":
            expr = sp.expand(ge_ - fe)
            min_val = _min_on_constraints(expr, v, lo, up)
            if min_val is None:
                return None
            return bool(min_val > 0)

        if pred.name == "le":
            expr = sp.expand(ge_ - fe)
            min_val = _min_on_constraints(expr, v, lo, up)
            if min_val is None:
                return None
            return bool(min_val >= 0)

        if pred.name == "ne":
            expr = sp.expand(fe - ge_)
            # 检查 expr = 0 是否在约束范围内有解
            # 方法：求 expr 在约束范围内的最小值/最大值，看 0 是否在其中
            min_v = _min_on_constraints(expr, v, lo, up)
            max_v = _min_on_constraints(-expr, v, lo, up)
            if min_v is None or max_v is None:
                return None
            return bool(min_v > 0 or max_v > 0)

    except Exception:
        return None

    return None


def _collect_var_names(term) -> set:
    """收集项里所有变量名"""
    result = set()
    tname = _type_name(term)
    if tname == 'Var':
        result.add(term.name)
    elif tname in ('Const', 'Pred'):
        for a in term.args:
            result |= _collect_var_names(a)
    return result


# ============================================================
# 引理评估
# ============================================================

def evaluate_lemma_generality(head, body) -> float:
    """
    评估引理的一般性。
    返回 0.0 ~ 1.0。
    """
    G = 1.0
    # 约束数量
    G -= 0.2 * len(body)
    # 变量被具体值替换
    var_names = _collect_var_names(head)
    const_count = 0
    for arg in (head.args if _type_name(head) == 'Pred' else []):
        if _type_name(arg) == 'Const':
            const_count += 1
    if const_count > 0 and len(var_names) == 0:
        G -= 0.5
    return max(0.0, G)


def evaluate_lemma_cost(proof_steps) -> int:
    """评估引理证明的步骤数（包括子引理）"""
    return len(proof_steps)


def should_cache_lemma(generality: float, cost: int, threshold: float = 1.5) -> bool:
    """
    判断是否值得缓存。
    缓存分数 = G * (1 + log(C))
    """
    import math
    if generality <= 0:
        return False
    score = generality * (1 + math.log(max(cost, 1)))
    return score >= threshold


def extract_search_range(body, var_name):
    """
    从 body 里提取 var_name 的搜索范围。
    返回 (lower, upper)，None 表示无界。
    """
    lower = None
    upper = None

    def walk(t):
        nonlocal lower, upper
        tn = _type_name(t)
        if tn == 'Pred':
            if t.name == "gt" and len(t.args) == 2:
                a, b = t.args
                if _type_name(a) == 'Var' and a.name == var_name:
                    lower = b
            elif t.name == "ge" and len(t.args) == 2:
                a, b = t.args
                if _type_name(a) == 'Var' and a.name == var_name:
                    lower = b
            elif t.name == "lt" and len(t.args) == 2:
                a, b = t.args
                if _type_name(a) == 'Var' and a.name == var_name:
                    upper = b
            elif t.name == "le" and len(t.args) == 2:
                a, b = t.args
                if _type_name(a) == 'Var' and a.name == var_name:
                    upper = b
            for a in t.args:
                walk(a)
        elif tn == 'Const':
            for a in t.args:
                walk(a)

    walk(body)
    return lower, upper

# ============================================================
# 素因子分析
# ============================================================

def prime_factorization(n: int) -> dict:
    """
    返回 n 的素因子分解 {p: e}。
    例如 12 -> {2: 2, 3: 1}。
    """
    if n <= 0:
        return {}
    return dict(sp.factorint(n))


def prime_power_in_factorial(p: int, n: int) -> int:
    """
    n! 里 p 的幂次（Legendre 公式）。
    v_p(n!) = floor(n/p) + floor(n/p^2) + ...
    """
    total = 0
    while n > 0:
        n //= p
        total += n
    return total


def prime_power_in(n: int, p: int) -> int:
    """
    n 里 p 的幂次。
    """
    if n <= 0:
        return 0
    count = 0
    while n % p == 0:
        n //= p
        count += 1
    return count