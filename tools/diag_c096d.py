# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 16:30:53 2026

@author: gzche
"""

# tools/diag_c096d.py
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
with open("theorems/concept_neurons.json", encoding="utf-8") as f:
    data = json.load(f)
nid = "NEURON::S::pythagorean<-exists::arity=3"
n = data["concept_neurons"].get(nid)
if n:
    print(f"lower: {n.get('lower')}")
    print(f"len(lower): {len(n.get('lower', []))}")
    print(f"hp: {n.get('head_pattern')}")