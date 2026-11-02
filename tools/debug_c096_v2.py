# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 16:15:01 2026

@author: gzche
"""

# tools/debug_c096_v2.py
import sys, os, json, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from adaptive_store import AdaptiveStore
from recursive_prover import RecursiveProver
from numtheory_prover import parse_goal

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
n = store.concept_neurons.get("NEURON::S::pythagorean<-exists::arity=3")
print(f"[debug] store.concept_neurons 里的 pythagorean: hp={n.get('head_pattern') if n else 'MISSING'}")

if hasattr(store, "_head_index"):
    print(f"[debug3] _head_index['exists']: {store._head_index.get('exists', [])}")
else:
    print(f"[debug3] _head_index 未建")
rp = RecursiveProver(store, iso_edges_path="data/iso_edges.json", verbose=True)
if hasattr(store, "_head_index"):
    print(f"[debug3] _head_index['exists']: {store._head_index.get('exists', [])}")
else:
    print(f"[debug3] _head_index 未建")
n = store.concept_neurons.get("NEURON::S::pythagorean<-exists::arity=3")
print(f"[debug2] after RecursiveProver: hp={n.get('head_pattern') if n else 'MISSING'}")
rp.prove(
    "exists(m, exists(n, and(gt(m,n), and(coprime(m,n), and(equals(a, minus(power(m,2),power(n,2))), and(equals(b, times(2,times(m,n))), equals(c, plus(power(m,2),power(n,2)))))))))",
    premises=["equals(plus(power(a,2),power(b,2)), power(c,2))","gt(a,0)","gt(b,0)","gt(c,0)"],
    verbose=True,
)