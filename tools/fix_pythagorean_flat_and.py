# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 23:14:06 2026

@author: gzche
"""

# tools/fix_pythagorean_flat_and.py
"""13.0.5：将 S::pythagorean 的 head_pattern 改成扁平 and。"""
import json, os, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

path = "theorems/concept_neurons.json"
shutil.copy2(path, path + ".bak_flat_and")

with open(path, encoding="utf-8") as f:
    data = json.load(f)

nid = "NEURON::S::pythagorean<-exists::arity=3"
n = data["concept_neurons"].get(nid)
if n is None:
    print(f"[MISSING] {nid}")
else:
    old_hp = n.get("head_pattern")
    # 扁平 and(gt, coprime, equals, equals, equals)
    n["head_pattern"] = [
        "exists",
        [
            "m",
            "exists(n, and(gt(m,n), coprime(m,n), equals(a, minus(power(m,2),power(n,2))), equals(b, times(2,times(m,n))), equals(c, plus(power(m,2),power(n,2)))))"
        ]
    ]
    print(f"[{nid}]")
    print(f"  old hp: {old_hp}")
    print(f"  new hp: {n['head_pattern']}")

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"[done] 写入 {path}, 总神经元: {len(data['concept_neurons'])}")