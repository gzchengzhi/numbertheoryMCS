import sys, os, json, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from adaptive_store import AdaptiveStore
from recursive_prover import RecursiveProver

store = AdaptiveStore()
for f in sorted(glob.glob("theorems/*.jsonl")):
    store.load_jsonl(f)
for f in sorted(glob.glob("theorems/12_0_competition/*.jsonl")):
    store.load_jsonl(f)

with open(os.path.join(ROOT, "theorems", "concept_neurons.json"), encoding="utf-8") as fh:
    data = json.load(fh)
store.concept_neurons = data["concept_neurons"]

print("=" * 70)
print("运行时 store.concept_neurons 关键神经元检查")
print("=" * 70)
for nid in [
    "NEURON::SP::congruent<-congruent+congruent::arity=3",
    "NEURON::SP::congruent<-coprime+prime::arity=3",
    "NEURON::SP::congruent<-coprime+gt::arity=3",
    "NEURON::S::congruent<-prime+gt::arity=3",
]:
    n = store.concept_neurons.get(nid)
    if n is None:
        print(f"  {nid}: ❌ 不在 store 里")
    else:
        print(f"  {nid}:")
        print(f"    head_pattern = {n.get('head_pattern')!r}")
        print(f"    lower = {n.get('lower')}")

print("\n" + "=" * 70)
print("_try_recursive 里 hp=None 时实际行为")
print("=" * 70)
import inspect
src = inspect.getsource(RecursiveProver._try_recursive)
has_none_check = "if hp is None:" in src
has_continue_after_none = "if hp is None:" in src and "continue" in src.split("if hp is None:")[1].split("\n")[1]
print(f"  源码里有 'if hp is None:': {has_none_check}")
print(f"  源码里 hp is None 后跟 continue: {has_continue_after_none}")

# 实际调一次 L4
rp = RecursiveProver(store, iso_edges_path=os.path.join(ROOT, "data", "iso_edges.json"))
proof = rp.prove("congruent(plus(a,c), plus(b,d), m)",
                 premises=["congruent(a, b, m)", "congruent(c, d, m)"],
                 verbose=True)
print(f"\nL4 结果: {[s.strategy for s in (proof or [])]}")