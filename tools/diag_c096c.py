# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 16:18:43 2026

@author: gzche
"""

# tools/diag_c096c.py
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
with open("theorems/concept_neurons.json", encoding="utf-8") as f:
    data = json.load(f)
for nid, n in data["concept_neurons"].items():
    if "pythagorean" in nid:
        print(f"{nid}: hp={n.get('head_pattern')}")