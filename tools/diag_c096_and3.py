# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 23:09:50 2026

@author: gzche
"""

# tools/diag_c096_and3.py
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from numtheory_prover import parse_goal, parse_term, unify
from recursive_prover import RecursiveProver

goal = parse_goal("exists(m, exists(n, and(gt(m,n), and(coprime(m,n), and(equals(a, minus(power(m,2),power(n,2))), and(equals(b, times(2,times(m,n))), equals(c, plus(power(m,2),power(n,2)))))))))")
# goal: exists(n, and(gt, and(coprime, and(equals(a,minus), and(equals(b,times), equals(c,plus))))))
g = goal.args[1].args[1].args[1]   # and(equals(a,minus), and(equals(b,times), equals(c,plus)))
g_and3 = g.args[1]   # and(equals(b,times), equals(c,plus))

rp = RecursiveProver.__new__(RecursiveProver)
a = rp._arg("exists(n, and(gt(m,n), and(coprime(m,n), and(equals(a, minus(power(m,2),power(n,2))), and(equals(b, times(2,times(m,n))), equals(c, plus(power(m,2),power(n,2)))))))))")
a_and3 = a.args[1].args[1].args[1].args[1]   # and(equals(b,times), equals(c,plus))

print("=== and3 ===")
print(f"goal: {g_and3}")
print(f"_arg: {a_and3}")
for i, (ga, aa) in enumerate(zip(g_and3.args, a_and3.args)):
    print(f"\nand3.args[{i}]:")
    print(f"  goal: {ga}, type={type(ga).__name__}, args={ga.args if hasattr(ga, 'args') else None}")
    print(f"  _arg: {aa}, type={type(aa).__name__}, args={aa.args if hasattr(aa, 'args') else None}")
    print(f"  unify: {unify(aa, ga, {})}")
    if hasattr(ga, "args") and hasattr(aa, "args"):
        for j, (gg, aaa) in enumerate(zip(ga.args, aa.args)):
            print(f"    args[{j}]: goal={gg}, _arg={aaa}, unify={unify(aaa, gg, {})}")