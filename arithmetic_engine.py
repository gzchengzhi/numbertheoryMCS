"""
数论计算引擎：为证明器提供"具体数值"计算能力
"""

import math
from typing import Any, Optional
from functools import lru_cache


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
    from numtheory_prover import Var, Const

    if isinstance(term, Var):
        if env and term.name in env:
            return evaluate(env[term.name], env)
        raise ValueError(f"未绑定变量: {term.name}")

    if isinstance(term, Const):
        if not term.args:
            # 常量：尝试转成 int
            try:
                return int(term.name)
            except ValueError:
                return term.name
        # 递归求值参数
        args = [evaluate(a, env) for a in term.args]
        return apply_function(term.name, args)

    # 字符串/数字
    if isinstance(term, (int, float)):
        return term
    if isinstance(term, str):
        try:
            return int(term)
        except ValueError:
            return term

    raise ValueError(f"无法求值: {term}")


def apply_function(name: str, args: list) -> Any:
    """根据函数名和参数求值"""
    if name == "plus":
        return args[0] + args[1]
    if name == "minus":
        return args[0] - args[1]
    if name == "times":
        return args[0] * args[1]
    if name == "div":
        return args[0] // args[1]
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


# ============================================================
# 谓词求值（核心接口）
# ============================================================

def evaluate_predicate(pred) -> Optional[bool]:
    """
    尝试计算一个谓词的真值。
    返回 True / False / None（无法计算）
    """
    from numtheory_prover import Var, Const, Pred

    # 检查是否所有参数都是具体值（无自由变量）
    def has_var(t):
        if isinstance(t, Var):
            return True
        if isinstance(t, Const):
            return any(has_var(a) for a in t.args)
        return False

    for a in pred.args:
        if has_var(a):
            return None  # 有变量，交给逻辑层

    name = pred.name

    try:
        args = [evaluate(a) for a in pred.args]
    except Exception:
        return None

    # 具体数值求值
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