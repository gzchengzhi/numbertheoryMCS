# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 11:50:47 2026

@author: gzche
"""

# tools/fix_c065.py
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
path = "tests/bench/competition/cases.jsonl"

with open(path, encoding="utf-8") as f:
    lines = [json.loads(l) for l in f if l.strip()]

for rec in lines:
    if rec["id"] == "C065":
        rec["premises"] = ["prime(2)"]
        print(f"修正 C065: premises=['prime(2)']")

with open(path, "w", encoding="utf-8") as f:
    for rec in lines:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")