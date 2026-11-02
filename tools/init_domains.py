# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 19:02:03 2026

@author: gzche
"""

# tools/init_domains.py
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

for name in ["dirichlet", "elliptic"]:
    os.makedirs(f"domains/{name}", exist_ok=True)
    # 空神经元
    with open(f"domains/{name}/concept_neurons.json", "w", encoding="utf-8") as f:
        json.dump({"concept_neurons": {}, "neuron_edges": {}}, f, ensure_ascii=False, indent=2)
    # 空 iso_edges
    with open(f"domains/{name}/iso_edges.json", "w", encoding="utf-8") as f:
        json.dump({"version": "1.0", "edges": []}, f, ensure_ascii=False, indent=2)
    print(f"[init] domains/{name}/")