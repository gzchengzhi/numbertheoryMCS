# tools/debug_c055.py
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

# 不用 bench_competition 的 monkey-patch，直接用原始 RecursiveProver
rp = RecursiveProver(store, iso_edges_path="data/iso_edges.json", verbose=True)

goal = parse_goal("irrational(sqrt(p))")
premises = [parse_goal("prime(p)")]
print("goal:", goal)
print("premises:", premises)

# 检查 head 索引（原始 _try_recursive 用 _sorted_neurons，不建 _head_index）
print("n_neurons:", len(store.concept_neurons))
print("has S::irrational<-prime:", "NEURON::S::irrational<-prime::arity=1" in store.concept_neurons)
n = store.concept_neurons.get("NEURON::S::irrational<-prime::arity=1")
print("hp:", n.get("head_pattern") if n else None)
print("lower:", n.get("lower") if n else None)

# 手动匹配
from numtheory_prover import unify
hp = n["head_pattern"]
pred = RecursiveProver.__new__(RecursiveProver)
from numtheory_prover import Pred
pat = Pred(hp[0], tuple(pred._arg(a) for a in hp[1]))
print("pat:", pat)
print("unify(pat, goal):", unify(pat, goal, {}))

# 手动调 _try_recursive（原始版，不走 head 索引）
r = rp._try_recursive(goal, premises, 0, set())
print("_try_recursive result:", r)