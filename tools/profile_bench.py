# tools/profile_bench.py
"""对 120 题逐题计时，找出慢题。"""
import sys, os, json, time, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from adaptive_store import AdaptiveStore
from recursive_prover import RecursiveProver

def make_rp():
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
    return RecursiveProver(store, iso_edges_path="data/iso_edges.json")

cases = []
with open("tests/bench/competition/cases.jsonl", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            cases.append(json.loads(line))

slow = []
for case in cases:
    rp = make_rp()
    t0 = time.time()
    try:
        proof = rp.prove(case["goal"], premises=case.get("premises", []), verbose=False)
    except Exception as e:
        proof = None
    elapsed = time.time() - t0
    slow.append((elapsed, case["id"], "✅" if proof else "❌"))

slow.sort(reverse=True)
print("Top 20 最慢的题：")
for elapsed, cid, status in slow[:20]:
    print(f"  {elapsed:6.2f}s  {cid}  {status}")
print(f"\n总耗时: {sum(s[0] for s in slow):.2f}s")
print(f"平均: {sum(s[0] for s in slow)/len(slow):.2f}s")