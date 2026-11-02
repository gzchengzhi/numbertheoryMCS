# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 16:09:44 2026

@author: gzche
"""

# tools/fix_c084_neuron.py
import json, os, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
path = "theorems/concept_neurons.json"

shutil.copy2(path, path + ".bak")

with open(path, encoding="utf-8") as f:
    data = json.load(f)

nid = "NEURON::S::periodic_cf_sqrt2::arity=2"
n = data["concept_neurons"].get(nid)
if n:
    old = n.get("head_pattern")
    n["head_pattern"] = ["periodic_continued_fraction", ["sqrt(2)", "list(1,2,2,2)"]]
    print(f"[{nid}] old: {old}")
    print(f"[{nid}] new: {n['head_pattern']}")
else:
    print(f"[MISSING] {nid}")

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"[done] 写入 {path}")