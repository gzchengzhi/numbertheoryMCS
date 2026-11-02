import sys, os, json, glob, traceback
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from adaptive_store import AdaptiveStore
from recursive_prover import RecursiveProver

store = AdaptiveStore()
for f in sorted(glob.glob("theorems/*.jsonl")):
    store.load_jsonl(f)
store.load_jsonl("theorems/12_0_competition.jsonl")
with open("theorems/concept_neurons.json", encoding="utf-8") as fh:
    data = json.load(fh)
store.concept_neurons = data["concept_neurons"]
store._neurons_built = True

rp = RecursiveProver(store, iso_edges_path="data/iso_edges.json")
try:
    r = rp.prove("congruent(power(a, minus(p,1)), 1, p)",
                 premises=["prime(p)", "not_divides(p, a)"],
                 verbose=False)
    print("OK:", r)
except Exception:
    traceback.print_exc()