# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 16:09:18 2026

@author: gzche
"""

# tools/fix_c084.py
"""修正 C084 的 goal：把 [1,2,2,2] 改成 list(1,2,2,2)。"""
import json, os, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
path = "tests/bench/competition/cases.jsonl"

# 备份
bak = "tests/bench/competition/cases.jsonl.bak"
shutil.copy2(path, bak)
print(f"[backup] -> {bak}")

# 读
lines = []
with open(path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            lines.append(json.loads(line))

# 改
for rec in lines:
    if rec["id"] == "C084":
        old_goal = rec["goal"]
        rec["goal"] = "periodic_continued_fraction(sqrt(2), list(1,2,2,2))"
        print(f"[C084] old: {old_goal}")
        print(f"[C084] new: {rec['goal']}")

# 写
with open(path, "w", encoding="utf-8") as f:
    for rec in lines:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
print(f"[done] 写入 {path}")