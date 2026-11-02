# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 15:54:07 2026

@author: gzche
"""

# tools/diag_c084.py
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from numtheory_prover import parse_goal, parse_term
from recursive_prover import RecursiveProver

# goal 解析
g = parse_goal("periodic_continued_fraction(sqrt(2), [1,2,2,2])")
print("goal:", g)
print("goal.args[1]:", g.args[1], type(g.args[1]).__name__)
if hasattr(g.args[1], "args"):
    print("goal.args[1].args:", g.args[1].args)

# _arg 解析
rp = RecursiveProver.__new__(RecursiveProver)
for s in ["sqrt(2)", "list(1,2,2,2)", "[1,2,2,2]"]:
    a = rp._arg(s)
    print(f"_arg({s!r}): {a}, type={type(a).__name__}", a.args if hasattr(a, "args") else None)