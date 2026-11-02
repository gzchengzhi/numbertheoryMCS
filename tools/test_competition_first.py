# tools/test_competition_first.py
"""
12.0 竞赛题测试：第一道传递题。
不改 11.0 任何源码，只在测试脚本里直接给 store.concept_neurons 赋值，
绕开 load_neurons 可能存在的 cwd 问题。
"""
import sys, os, json, glob

# 强制 cwd 到项目根（tools/ 的上一级）
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

print(f"[debug] cwd = {os.getcwd()}")
print(f"[debug] ROOT = {ROOT}")

from adaptive_store import AdaptiveStore
from recursive_prover import RecursiveProver

# 1. 加载定理
store = AdaptiveStore()
for f in sorted(glob.glob("theorems/*.jsonl")):
    store.load_jsonl(f)
for f in sorted(glob.glob("theorems/12_0_competition/*.jsonl")):
    if os.path.exists(f):
        store.load_jsonl(f)
print(f"[debug] clauses = {len(store.clauses)}")

# 2. 加载神经元 —— 不用 load_neurons，直接读 JSON 赋值
neuro_path = os.path.join(ROOT, "theorems", "concept_neurons.json")
print(f"[debug] neuro_path = {neuro_path}")
print(f"[debug] exists = {os.path.exists(neuro_path)}")
with open(neuro_path, "r", encoding="utf-8") as fh:
    data = json.load(fh)
print(f"[debug] 顶层 keys = {list(data.keys())}")
print(f"[debug] concept_neurons 数量 = {len(data.get('concept_neurons', {}))}")

store.concept_neurons = data.get("concept_neurons", {})
store.neuron_edges = {}
for key, w in data.get("neuron_edges", {}).items():
    parts = key.split("|")
    if len(parts) == 2:
        store.neuron_edges[(parts[0], parts[1])] = w
store._neurons_built = True

print(f"[debug] store.concept_neurons = {len(store.concept_neurons)}")
print(f"[debug] has T::divides = {'NEURON::T::divides::@0-@1::arity=2' in store.concept_neurons}")
assert len(store.concept_neurons) > 0, "concept_neurons 还是 0"

# 3. 构造 RecursiveProver，用绝对路径传 iso
iso_path = os.path.join(ROOT, "data", "iso_edges.json")
print(f"[debug] iso_path = {iso_path}, exists = {os.path.exists(iso_path)}")
rp = RecursiveProver(store, iso_edges_path=iso_path, verbose=True)

# 4. 跑传递题
proof = rp.prove(
    "divides(a, c)",
    premises=["divides(a, b)", "divides(b, c)"],
    verbose=True,
)
print("\n=== RESULT ===")
if proof:
    for s in proof:
        print(f"  strategy={s.strategy}  subgoal={s.subgoal}")
else:
    print("  未证明")