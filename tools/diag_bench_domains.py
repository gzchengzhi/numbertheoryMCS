# tools/diag_bench_domains.py
import sys, os, json, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from adaptive_store import AdaptiveStore
from concept_domain import DomainRegistry

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

before = len(store.concept_neurons)
reg = DomainRegistry("domains")
added = reg.load_all_into(store)
after = len(store.concept_neurons)

print(f"主库: {before}")
print(f"域加载: {added}")
print(f"总: {after}")
print(f"has C103 neuron: {'NEURON::S::not<-elliptic_curve::arity=1' in store.concept_neurons}")
print(f"has C104 neuron: {'NEURON::S::finitely_generated<-elliptic_curve::arity=1' in store.concept_neurons}")