# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 19:03:20 2026

@author: gzche
"""

# tools/init_dirichlet_cases.py
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

CASES = [
    {"id": "C098", "statement": "Dirichlet 特征 χ(1)=1",
     "goal": "equals(chi(1), 1)",
     "premises": ["dirichlet_character(chi, m)"]},
    {"id": "C099", "statement": "χ(ab) = χ(a)χ(b)",
     "goal": "equals(chi(times(a,b)), times(chi(a), chi(b)))",
     "premises": ["dirichlet_character(chi, m)"]},
    {"id": "C100", "statement": "gcd(a,m)>1 ⇒ χ(a)=0",
     "goal": "equals(chi(a), 0)",
     "premises": ["dirichlet_character(chi, m)", "gt(gcd(a,m), 1)"]},
    {"id": "C101", "statement": "非主特征的和 = 0",
     "goal": "equals(sum(a, 1, m, chi(a)), 0)",
     "premises": ["dirichlet_character(chi, m)", "not(is_principal_character(chi))"]},
    {"id": "C102", "statement": "Dirichlet 定理（模 m 素数无穷）",
     "goal": "forall(N, exists(p, and(prime(p), and(gt(p, N), congruent(p, a, m)))))",
     "premises": ["coprime(a, m)", "gt(m, 1)"]},
]

with open("domains/dirichlet/cases.jsonl", "w", encoding="utf-8") as f:
    for c in CASES:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")
print(f"[init] {len(CASES)} cases → domains/dirichlet/cases.jsonl")