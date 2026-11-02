# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 15:55:35 2026

@author: gzche
"""

# tools/diag_c096.py
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from numtheory_prover import parse_goal, parse_term
from recursive_prover import RecursiveProver

g = parse_goal("exists(m, exists(n, and(gt(m,n), and(coprime(m,n), and(equals(a, minus(power(m,2),power(n,2))), and(equals(b, times(2,times(m,n))), equals(c, plus(power(m,2),power(n,2)))))))))")
print("goal:", g)
print("goal.args[1]:", g.args[1], type(g.args[1]).__name__)
if hasattr(g.args[1], "args"):
    print("goal.args[1].args:", g.args[1].args)

rp = RecursiveProver.__new__(RecursiveProver)
s = "exists(n, and(gt(m,n), and(coprime(m,n), and(equals(a, minus(power(m,2),power(n,2))), and(equals(b, times(2,times(m,n))), equals(c, plus(power(m,2),power(n,2)))))))))"
a = rp._arg(s)
print(f"_arg(...): {a}, type={type(a).__name__}", a.args if hasattr(a, "args") else None)