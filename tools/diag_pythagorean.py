# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 19:20:07 2026

@author: gzche
"""

# tools/diag_pythagorean.py
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
with open("theorems/concept_neurons.json", encoding="utf-8") as f:
    data = json.load(f)
n = data["concept_neurons"].get("NEURON::S::pythagorean<-exists::arity=3")
print(f"construct: {n.get('construct')}")
print(f"总神经元: {len(data['concept_neurons'])}")