# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 19:04:14 2026

@author: gzche
"""

# tools/init_elliptic_cases.py
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

CASES = [
    {"id": "C103", "statement": "椭圆曲线判别式 Δ ≠ 0",
     "goal": "not(equals(discriminant_ec(E), 0))",
     "premises": ["elliptic_curve(E)"]},
    {"id": "C104", "statement": "Mordell-Weil 定理",
     "goal": "finitely_generated(ec_points(E))",
     "premises": ["elliptic_curve(E)"]},
    {"id": "C105", "statement": "Hasse 界",
     "goal": "le(abs(minus(count_points(E, p), plus(p, 1))), times(2, sqrt(p)))",
     "premises": ["elliptic_curve(E)"]},
    {"id": "C106", "statement": "群律结合性",
     "goal": "equals(add_ec(add_ec(P, Q), R), add_ec(P, add_ec(Q, R)))",
     "premises": ["elliptic_curve(E)"]},
    {"id": "C107", "statement": "无穷远点是单位元",
     "goal": "equals(add_ec(P, infinity), P)",
     "premises": ["elliptic_curve(E)"]},
]

with open("domains/elliptic/cases.jsonl", "w", encoding="utf-8") as f:
    for c in CASES:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")
print(f"[init] {len(CASES)} cases → domains/elliptic/cases.jsonl")