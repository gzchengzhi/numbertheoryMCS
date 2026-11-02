# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 18:33:38 2026

@author: gzche
"""

# tools/diag_c096_e.py
import sys, os, json, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from tools.bench_competition import make_rp, _build_indexes
from adaptive_store import AdaptiveStore

store = AdaptiveStore()
for f in sorted(glob.glob("theorems/*.jsonl")):
    base = os.path.basename(f)
    if "learn_log" in base or "candidates" in base:
        continue
    store.load_jsonl(f)
with open("theorems/concept_neurons.json", encoding="utf-8") as fh:
    data = json.load(fh)
store.concept_neurons = data["concept_neurons"]
store._neurons_built = True
if hasattr(store, "_head_index"):
    del store._head_index
_build_indexes(store)

print("_head_index['exists']:")
for nid in store._head_index.get("exists", []):
    n = store.concept_neurons.get(nid, {})
    print(f"  {nid}: hp={n.get('head_pattern') is not None}, construct={n.get('construct') is not None}")