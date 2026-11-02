# tools/debug_c096_v3.py
import sys, os, json, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

import tools.bench_competition as bench
from tools.bench_competition import _build_indexes
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
if hasattr(store, "_head_index"):
    del store._head_index
_build_indexes(store)
rp = RecursiveProver(store, iso_edges_path="data/iso_edges.json", verbose=True)
print(f"[debug] _try_recursive.__name__: {rp._try_recursive.__name__}")
print(f"[debug] _try_recursive.__qualname__: {rp._try_recursive.__qualname__}")
print(f"[debug] RecursiveProver._try_recursive: {RecursiveProver._try_recursive.__name__}")
goal = parse_goal("exists(m, exists(n, and(gt(m,n), and(coprime(m,n), and(equals(a, minus(power(m,2),power(n,2))), and(equals(b, times(2,times(m,n))), equals(c, plus(power(m,2),power(n,2)))))))))")
premises = [parse_goal("equals(plus(power(a,2),power(b,2)), power(c,2))"), parse_goal("gt(a,0)"), parse_goal("gt(b,0)"), parse_goal("gt(c,0)")]

# ★ 手动调 _try_recursive
r = rp._try_recursive(goal, premises, 0, set())
print("_try_recursive result:", r)