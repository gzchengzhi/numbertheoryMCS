# -*- coding: utf-8 -*-
"""
Created on Mon Nov  2 08:01:34 2026

@author: gzche
"""

# tools/diag_c096_main.py
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

with open("theorems/concept_neurons.json", encoding="utf-8") as f:
    data = json.load(f)

new_nid = "NEURON::S::exists<-c096_pythagorean::arity=1"
old_nid = "NEURON::S::pythagorean<-exists::arity=3"
print(f"new_nid in: {new_nid in data['concept_neurons']}")
print(f"old_nid in: {old_nid in data['concept_neurons']}")
if new_nid in data["concept_neurons"]:
    n = data["concept_neurons"][new_nid]
    print(f"new hp: {n.get('head_pattern')}")
    print(f"new lower: {n.get('lower')}")