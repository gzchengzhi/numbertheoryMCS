# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 11:46:57 2026

@author: gzche
"""

# tools/fix_c055.py
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
path = "tests/bench/competition/cases.jsonl"

with open(path, encoding="utf-8") as f:
    lines = [json.loads(l) for l in f if l.strip()]

for rec in lines:
    if rec["id"] == "C055":
        rec["goal"] = "irrational(sqrt(p))"
        rec["premises"] = ["prime(p)"]
        print(f"修正 C055: goal=irrational(sqrt(p)), premises=['prime(p)']")

with open(path, "w", encoding="utf-8") as f:
    for rec in lines:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")