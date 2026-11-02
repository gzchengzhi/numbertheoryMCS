# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 23:06:22 2026

@author: gzche
"""

# tools/diag_c096_and2.py
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from numtheory_prover import parse_goal, parse_term, unify
from recursive_prover import RecursiveProver

goal = parse_goal("exists(m, exists(n, and(gt(m,n), and(coprime(m,n), and(equals(a, minus(power(m,2),power(n,2))), and(equals(b, times(2,times(m,n))), equals(c, plus(power(m,2),power(n,2)))))))))")
g_and = goal.args[1].args[1]   # and(gt, and(coprime, and(...)))
g_and2 = g_and.args[1]         # and(coprime, and(...))

rp = RecursiveProver.__new__(RecursiveProver)
a = rp._arg("exists(n, and(gt(m,n), and(coprime(m,n), and(equals(a, minus(power(m,2),power(n,2))), and(equals(b, times(2,times(m,n))), equals(c, plus(power(m,2),power(n,2)))))))))")
a_and2 = a.args[1].args[1]

print("=== and2 ===")
print(f"goal: {g_and2}")
print(f"_arg: {a_and2}")
for i, (ga, aa) in enumerate(zip(g_and2.args, a_and2.args)):
    print(f"\nand2.args[{i}]:")
    print(f"  goal: {ga}, type={type(ga).__name__}, args={ga.args if hasattr(ga, 'args') else None}")
    print(f"  _arg: {aa}, type={type(aa).__name__}, args={aa.args if hasattr(aa, 'args') else None}")
    print(f"  unify: {unify(aa, ga, {})}")

# 如果是 and2.args[0] 的 coprime(m,n)
if len(g_and2.args) >= 1:
    g0, a0 = g_and2.args[0], a_and2.args[0]
    print(f"\n=== and2.args[0] 详细 ===")
    print(f"goal: {g0}, type={type(g0).__name__}")
    print(f"_arg: {a0}, type={type(a0).__name__}")
    if hasattr(g0, "args") and hasattr(a0, "args"):
        for j, (gg, aa) in enumerate(zip(g0.args, a0.args)):
            print(f"  g0.args[{j}]: goal={gg}, _arg={aa}, unify={unify(aa, gg, {})}")