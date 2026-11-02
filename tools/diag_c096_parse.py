# tools/diag_c096_parse.py
import sys, os, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from numtheory_prover import parse_goal, parse_term, unify, Pred
from recursive_prover import RecursiveProver

# goal 解析
goal = parse_goal("exists(m, exists(n, and(gt(m,n), and(coprime(m,n), and(equals(a, minus(power(m,2),power(n,2))), and(equals(b, times(2,times(m,n))), equals(c, plus(power(m,2),power(n,2)))))))))")
print(f"goal: {goal}")
print(f"goal.args[1]: {goal.args[1]}, type={type(goal.args[1]).__name__}")

# _arg 解析
rp = RecursiveProver.__new__(RecursiveProver)
a = rp._arg("exists(n, and(gt(m,n), and(coprime(m,n), and(equals(a, minus(power(m,2),power(n,2))), and(equals(b, times(2,times(m,n))), equals(c, plus(power(m,2),power(n,2)))))))))")
print(f"_arg: {a}, type={type(a).__name__}")
print(f"_arg.args: {a.args if hasattr(a, 'args') else None}")
print(f"unify: {unify(a, goal.args[1], {})}")

# premises 解析
prem = parse_goal("equals(plus(power(a,2),power(b,2)), power(c,2))")
print(f"prem: {prem}")
print(f"prem.args[0]: {prem.args[0]}, type={type(prem.args[0]).__name__}")
print(f"prem.args[1]: {prem.args[1]}, type={type(prem.args[1]).__name__}")

# _arg 解析 premises
p0 = rp._arg("plus(power(a,2),power(b,2))")
p1 = rp._arg("power(c,2)")
print(f"_arg(plus): {p0}, type={type(p0).__name__}")
print(f"_arg(power(c,2)): {p1}, type={type(p1).__name__}")
print(f"unify p0: {unify(p0, prem.args[0], {})}")
print(f"unify p1: {unify(p1, prem.args[1], {})}")