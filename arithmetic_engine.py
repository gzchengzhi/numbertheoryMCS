"""
数论计算引擎：为证明器提供"具体数值"计算能力
"""

import math
from typing import Any, Optional
from functools import lru_cache
import sympy as sp

def _type_name(term) -> str:
    """返回对象的类名，对 reload 免疫。"""
    return type(term).__name__


# ============================================================
# 表达式求值
# ============================================================

def evaluate(term, env: dict = None) -> Any:
    """
    递归求值一个项。
    term 可以是：
      - 数字字符串 '5'
      - 表达式对象 Const('plus', (a, b))
      - 变量 Var（查 env）
    """
    tname = _type_name(term)

    if tname == 'Var':
        if env and term.name in env:
            return evaluate(env[term.name], env)
        raise ValueError(f"未绑定变量: {term.name}")

    if tname == 'Const':
        # ---- sum 特殊处理 ----
        if term.name == "sum" and len(term.args) == 4:
            return _evaluate_sum(term, env)

        if not term.args:
            try:
                return int(term.name)
            except ValueError:
                return term.name
        args = [evaluate(a, env) for a in term.args]
        return apply_function(term.name, args)

    if isinstance(term, (int, float)):
        return term
    if isinstance(term, str):
        try:
            return int(term)
        except ValueError:
            return term

    raise ValueError(f"无法求值: {term}")
    
def _evaluate_sum(term, env):
    """
    求值 sum(i, lower, upper, body)。
    对 i 从 lower 到 upper，累加 body。
    """
    from numtheory_prover import Const

    var = term.args[0]       # Var("i")
    lower = term.args[1]
    upper = term.args[2]
    body = term.args[3]

    lo = evaluate(lower, env)
    up = evaluate(upper, env)

    if not isinstance(lo, int) or not isinstance(up, int):
        raise ValueError(f"sum 的上下界必须是整数: {lo}, {up}")

    total = 0
    for i_val in range(lo, up + 1):
        env2 = dict(env) if env else {}
        env2[var.name] = Const(str(i_val))
        total += evaluate(body, env2)
    return total


def apply_function(name: str, args: list) -> Any:
    """根据函数名和参数求值"""
    if name == "plus":
        return args[0] + args[1]
    if name == "minus":
        return args[0] - args[1]
    if name == "times":
        return args[0] * args[1]
    if name == "div":
        if args[1] == 0:
            raise ValueError("除以零")
        if args[0] % args[1] == 0:
            return args[0] // args[1]
        return sp.Rational(args[0], args[1])
    if name == "mod":
        return args[0] % args[1]
    if name == "power":
        return args[0] ** args[1]
    if name == "abs":
        return abs(args[0])
    if name == "gcd":
        return math.gcd(args[0], args[1])
    if name == "lcm":
        return abs(args[0] * args[1]) // math.gcd(args[0], args[1])
    if name == "phi":
        return euler_phi(args[0])
    if name == "tau":
        return divisor_count(args[0])
    if name == "sigma":
        return divisor_sum(args[0])
    if name == "factorial":
        return math.factorial(args[0])
    if name == "sqrt":
        return math.isqrt(args[0]) if args[0] >= 0 else None
    if name == "prime_factorization":
        from symbolic import prime_factorization
        return prime_factorization(args[0])
    if name == "prime_power":
        from symbolic import prime_power_in
        return prime_power_in(args[0], args[1])
    raise ValueError(f"未知函数: {name}")


# ============================================================
# 数论函数
# ============================================================

def is_prime(n: int) -> bool:
    """素性测试（Miller-Rabin 简化版 + 试除）"""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n ** 0.5) + 1, 2):
        if n % i == 0:
            return False
    return True


@lru_cache(maxsize=10000)
def euler_phi(n: int) -> int:
    """欧拉函数 φ(n)"""
    if n <= 0:
        return 0
    result = n
    p = 2
    temp = n
    while p * p <= temp:
        if temp % p == 0:
            while temp % p == 0:
                temp //= p
            result -= result // p
        p += 1
    if temp > 1:
        result -= result // temp
    return result


def divisor_count(n: int) -> int:
    """约数个数 τ(n)"""
    if n <= 0:
        return 0
    count = 0
    for i in range(1, int(n ** 0.5) + 1):
        if n % i == 0:
            count += 2 if i != n // i else 1
    return count


def divisor_sum(n: int) -> int:
    """约数和 σ(n)"""
    if n <= 0:
        return 0
    total = 0
    for i in range(1, int(n ** 0.5) + 1):
        if n % i == 0:
            total += i
            if i != n // i:
                total += n // i
    return total

def _is_integer_value(v):
    if isinstance(v, int):
        return True
    if hasattr(v, 'is_integer'):
        return bool(v.is_integer)
    if hasattr(v, 'q') and hasattr(v, 'p'):
        return v.q == 1
    return False


# ============================================================
# 谓词求值（核心接口）
# ============================================================

def evaluate_predicate(pred) -> Optional[bool]:
    """
    尝试计算一个谓词的真值。
    返回 True / False / None（无法计算）
    """
    tname = _type_name(pred)

    if tname not in ('Pred', 'Const'):
        return None

    name = pred.name

    # ---- and ----
    if name == "and":
        for a in pred.args:
            r = evaluate_predicate(a)
            if r is False:
                return False
            if r is None:
                return None
        return True

    # ---- or ----
    if name == "or":
        has_none = False
        for a in pred.args:
            r = evaluate_predicate(a)
            if r is True:
                return True
            if r is None:
                has_none = True
        return None if has_none else False

    # ---- integer / not_integer（必须在 has_var 之前）----
    if name in ("integer", "not_integer"):
        try:
            args = [evaluate(a) for a in pred.args]
        except Exception:
            return None
        if name == "integer":
            return _is_integer_value(args[0])
        return not _is_integer_value(args[0])

    # ---- 已知谓词 ----
    KNOWN_PREDICATES = {
        "divides", "equals", "gt", "lt", "ge", "le", "ne",
        "prime", "composite", "coprime", "congruent",
        "nonzero", "even", "odd", "square", "perfect",
        "integer", "not_integer",
        "prime_power", "prime_power_in_factorial",
        "has_prime_factor", "not_divides",
    }   
    if name not in KNOWN_PREDICATES:
        return None
    


    # ---- has_var 检查 ----
    def has_var(t):
        tn = _type_name(t)
        if tn == 'Var':
            return True
        if tn in ('Const', 'Pred'):
            return any(has_var(a) for a in t.args)
        return False

    for a in pred.args:
        if has_var(a):
            return None

    # ---- 求值 ----
    try:
        args = [evaluate(a) for a in pred.args]
    except Exception:
        return None

    # ---- 具体数值求值 ----
    
    # ---- prime_power ----
    if name == "prime_power":
        n, p, e = args
        from symbolic import prime_power_in
        return prime_power_in(n, p) == e
    
    # ---- prime_power_in_factorial ----
    if name == "prime_power_in_factorial":
        n, p, e = args
        from symbolic import prime_power_in_factorial
        return prime_power_in_factorial(p, n) == e
    
    # ---- has_prime_factor ----
    if name == "has_prime_factor":
        n, p = args
        from symbolic import prime_power_in
        return prime_power_in(n, p) > 0
    
    if name == "not_divides":
        a, b = args
        if a == 0:
            return b != 0
        return b % a != 0
    
    if name == "divides":
        a, b = args
        if a == 0:
            return b == 0
        return b % a == 0

    if name == "equals":
        return args[0] == args[1]

    if name == "gt":
        return args[0] > args[1]

    if name == "lt":
        return args[0] < args[1]

    if name == "ge":
        return args[0] >= args[1]

    if name == "le":
        return args[0] <= args[1]

    if name == "ne":
        return args[0] != args[1]

    if name == "prime":
        return is_prime(args[0])

    if name == "composite":
        return args[0] > 1 and not is_prime(args[0])

    if name == "coprime":
        return math.gcd(args[0], args[1]) == 1

    if name == "congruent":
        a, b, m = args
        if m <= 0:
            return None
        return (a - b) % m == 0

    if name == "nonzero":
        return args[0] != 0

    if name == "even":
        return args[0] % 2 == 0

    if name == "odd":
        return args[0] % 2 == 1

    if name == "square":
        if args[0] < 0:
            return False
        r = math.isqrt(args[0])
        return r * r == args[0]

    if name == "perfect":
        n = args[0]
        return n > 0 and divisor_sum(n) == 2 * n

    return None


# ============================================================
# 自测
# ============================================================

if __name__ == "__main__":
    from numtheory_prover import make_pred, make_const

    tests = [
        ("divides(2, 4)", True),
        ("divides(3, 6)", True),
        ("divides(5, 5)", True),
        ("divides(7, 728)", True),
        ("prime(7)", True),
        ("prime(10)", False),
        ("coprime(3, 7)", True),
        ("congruent(7, 2, 5)", True),
        ("congruent(3, 5, 7)", False),
        ("equals(phi(10), 4)", True),
        ("equals(tau(12), 6)", True),
        ("equals(power(3, 6), 729)", True),
    ]

    from numtheory_prover import parse_goal

    for expr, expected in tests:
        pred = parse_goal(expr)
        result = evaluate_predicate(pred)
        status = "✅" if result == expected else "❌"
        print(f"  {status} {expr} → {result} (期望 {expected})")