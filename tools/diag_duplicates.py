# tools/diag_duplicates.py
import sys, os, json, glob
from collections import defaultdict

# 项目根目录 = tools/ 的上一级
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
print(f"[diag] 项目根目录: {ROOT}")
print(f"[diag] cwd: {os.getcwd()}")


import json, glob, os, sys
from collections import defaultdict

files = sorted(glob.glob("theorems/**/*.jsonl", recursive=True))
print(f"扫描 {len(files)} 个文件：")
for f in files:
    print(f"  {f}")

id_occ = defaultdict(list)
for f in files:
    with open(f, "r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            cid = rec.get("id")
            if cid:
                id_occ[cid].append((f, line_no, rec.get("category", "")))

dups = {k: v for k, v in id_occ.items() if len(v) > 1}
print(f"\n总 id 数: {len(id_occ)}")
print(f"重复 id 数: {len(dups)}")
print(f"可删除条数: {sum(len(v) - 1 for v in dups.values())}")

# 按文件对统计
pair_count = defaultdict(int)
for cid, occs in dups.items():
    for i in range(len(occs)):
        for j in range(i + 1, len(occs)):
            pair = tuple(sorted([occs[i][0], occs[j][0]]))
            pair_count[pair] += 1

print("\n重复来源（文件对）:")
for pair, count in sorted(pair_count.items(), key=lambda x: -x[1])[:20]:
    print(f"  {pair[0]}  ↔  {pair[1]}: {count} 个重复 id")