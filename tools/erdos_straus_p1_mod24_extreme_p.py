# tools/erdos_straus_p1_mod24_extreme_p.py
"""提取 r_min >= 31 的极端 p，分析它们的模类与 N_r 结构。"""
import json
from sympy import factorint

with open("theorems/20_4_min_r_analysis.json", encoding="utf-8") as f:
    data = json.load(f)

results = data["results"]
extreme = [r for r in results if r["r_min"] >= 31]
print(f"r_min >= 31 的 p 数量: {len(extreme)}")
print(f"r_min 分布: {[(r['r_min'], sum(1 for x in extreme if x['r_min']==r['r_min'])) for r in extreme[:10]]}")

# 打印前 20 个极端 p
for rec in extreme[:20]:
    p, r = rec["p"], rec["r_min"]
    # p mod 24 固定为 1
    # p mod r 是多少？
    print(f"p={p}, r_min={r}, p mod r = {p % r}, p mod 24 = {p % 24}")