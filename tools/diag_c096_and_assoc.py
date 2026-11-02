# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 23:10:47 2026

@author: gzche
"""

# tools/diag_c096_and_assoc.py
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from numtheory_prover import parse_goal, parse_term

# parse_goal 的 and
g = parse_goal("exists(n, and(gt(m,n), and(coprime(m,n), and(equals(a, minus(power(m,2),power(n,2))), and(equals(b, times(2,times(m,n))), equals(c, plus(power(m,2),power(n,2)))))))))")
print("=== parse_goal ===")
print(f"g: {g}")
print(f"g.args: {g.args}")
if hasattr(g.args[1], "args"):
    print(f"g.args[1] (and): {g.args[1]}")
    print(f"g.args[1].args: {g.args[1].args}")
    print(f"g.args[1].args[0]: {g.args[1].args[0]}")
    print(f"g.args[1].args[1]: {g.args[1].args[1]}")
    if hasattr(g.args[1].args[1], "args"):
        print(f"g.args[1].args[1].args: {g.args[1].args[1].args}")

# parse_term 的 and
t = parse_term("exists(n, and(gt(m,n), and(coprime(m,n), and(equals(a, minus(power(m,2),power(n,2))), and(equals(b, times(2,times(m,n))), equals(c, plus(power(m,2),power(n,2)))))))))")
print("\n=== parse_term ===")
print(f"t: {t}")
print(f"t.args: {t.args}")
if hasattr(t.args[1], "args"):
    print(f"t.args[1] (and): {t.args[1]}")
    print(f"t.args[1].args: {t.args[1].args}")
    print(f"t.args[1].args[0]: {t.args[1].args[0]}")
    print(f"t.args[1].args[1]: {t.args[1].args[1]}")
    if hasattr(t.args[1].args[1], "args"):
        print(f"t.args[1].args[1].args: {t.args[1].args[1].args}")