# tools/diag_c096_and.py
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from numtheory_prover import parse_goal, parse_term, unify, Pred

# goal 的 exists(n, and(...))
goal = parse_goal("exists(m, exists(n, and(gt(m,n), and(coprime(m,n), and(equals(a, minus(power(m,2),power(n,2))), and(equals(b, times(2,times(m,n))), equals(c, plus(power(m,2),power(n,2)))))))))")
g_inner = goal.args[1]   # exists(n, and(...))
g_and = g_inner.args[1]  # and(...)
print(f"goal and: {g_and}, type={type(g_and).__name__}")
print(f"goal and.args: {g_and.args if hasattr(g_and, 'args') else None}")

# _arg 的 exists(n, and(...))
from recursive_prover import RecursiveProver
rp = RecursiveProver.__new__(RecursiveProver)
a = rp._arg("exists(n, and(gt(m,n), and(coprime(m,n), and(equals(a, minus(power(m,2),power(n,2))), and(equals(b, times(2,times(m,n))), equals(c, plus(power(m,2),power(n,2)))))))))")
a_and = a.args[1]
print(f"_arg and: {a_and}, type={type(a_and).__name__}")
print(f"_arg and.args: {a_and.args if hasattr(a_and, 'args') else None}")

# 逐层 unify
print(f"unify exists: {unify(a, g_inner, {})}")
print(f"unify and: {unify(a_and, g_and, {})}")

# 逐层对比 and 的参数
if hasattr(g_and, 'args') and hasattr(a_and, 'args'):
    for i, (ga, aa) in enumerate(zip(g_and.args, a_and.args)):
        print(f"and.args[{i}]:")
        print(f"  goal: {ga}, type={type(ga).__name__}")
        print(f"  _arg: {aa}, type={type(aa).__name__}")
        print(f"  unify: {unify(aa, ga, {})}")