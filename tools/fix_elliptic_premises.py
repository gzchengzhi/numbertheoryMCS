# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 20:20:09 2026

@author: gzche
"""

# tools/fix_elliptic_premises.py
import json, os, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
path = "tests/bench/competition/cases.jsonl"
shutil.copy2(path, path + ".bak_elliptic")

with open(path, encoding="utf-8") as f:
    lines = [json.loads(l) for l in f if l.strip()]

for rec in lines:
    if rec["id"] in ("C103", "C104", "C105", "C106", "C107"):
        rec["premises"] = ["elliptic_curve(E)"]
        print(f"[{rec['id']}] premises → {rec['premises']}")

with open(path, "w", encoding="utf-8") as f:
    for rec in lines:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
print(f"[done] 写入 {path}")