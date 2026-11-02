# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 16:03:12 2026

@author: gzche
"""

# tools/diag_c084b.py
import sys, os, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

with open("theorems/concept_neurons.json", encoding="utf-8") as f:
    data = json.load(f)

nid = "NEURON::S::periodic_cf_sqrt2::arity=2"
n = data["concept_neurons"].get(nid)
if n is None:
    print(f"[MISSING] {nid} 不在")
else:
    print(f"hp: {n.get('head_pattern')}")
    print(f"lower: {n.get('lower')}")