# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 23:07:38 2026

@author: gzche
"""

# tools/diag_c096_equals.py
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from numtheory_prover import parse_goal, parse_term, unify
from recursive_prover import RecursiveProver

goal = parse_goal("exists(m, exists(n, and(gt(m,n), and(coprime(m,n), and(equals(a, minus(power(m,2),power(n,2))), and(equals(b, times(2,times(m,n))), equals(c, plus(power(m,2),power(n,2)))))))))")
# 导航到 equals(a, minus(power(m,2),power(n,2)))
# and(gt, and(coprime, and(equals, and(equals, equals))))
g_eq = goal.args[1].args[1].args[1].args[1].args[0]   # equals(a, minus(power(m,2),power(n,2)))
print(f"goal eq: {g_eq}, type={type(g_eq).__name__}, args={g_eq.args if hasattr(g_eq, 'args') else None}")

rp = RecursiveProver.__new__(RecursiveProver)
a = rp._arg("exists(n, and(gt(m,n), and(coprime(m,n), and(equals(a, minus(power(m,2),power(n,2))), and(equals(b, times(2,times(m,n))), equals(c, plus(power(m,2),power(n,2)))))))))")
a_eq = a.args[1].args[1].args[1].args[0]
print(f"_arg eq: {a_eq}, type={type(a_eq).__name__}, args={a_eq.args if hasattr(a_eq, 'args') else None}")

print(f"unify eq: {unify(a_eq, g_eq, {})}")

# 逐层
for i, (ga, aa) in enumerate(zip(g_eq.args, a_eq.args)):
    print(f"\neq.args[{i}]:")
    print(f"  goal: {ga}, type={type(ga).__name__}, args={ga.args if hasattr(ga, 'args') else None}")
    print(f"  _arg: {aa}, type={type(aa).__name__}, args={aa.args if hasattr(aa, 'args') else None}")
    print(f"  unify: {unify(aa, ga, {})}")
    if hasattr(ga, "args") and hasattr(aa, "args"):
        for j, (gg, aaa) in enumerate(zip(ga.args, aa.args)):
            print(f"    args[{j}]: goal={gg}, _arg={aaa}, unify={unify(aaa, gg, {})}")