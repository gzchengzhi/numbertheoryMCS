# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 16:13:57 2026

@author: gzche
"""

# tools/diag_c096b.py
import sys, os, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

with open("theorems/concept_neurons.json", encoding="utf-8") as f:
    data = json.load(f)

nid = "NEURON::S::pythagorean<-exists::arity=3"
n = data["concept_neurons"].get(nid)
if n is None:
    print(f"[MISSING] {nid}")
else:
    print(f"type: {n.get('type')}")
    print(f"lower: {n.get('lower')}")
    print(f"hp: {n.get('head_pattern')}")