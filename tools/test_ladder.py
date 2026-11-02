# tools/test_ladder.py
"""
12.0 竞赛题难度阶梯。只加测试脚本，不改 11.0 源码。
每跑完一题，记录 strategy，看哪一层点火。
"""
import sys, os, json, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from adaptive_store import AdaptiveStore
from recursive_prover import RecursiveProver

# ---- 加载（和 test_competition_first.py 一致）----
store = AdaptiveStore()
for f in sorted(glob.glob("theorems/*.jsonl")):
    store.load_jsonl(f)
# 新
comp_file = os.path.join(ROOT, "theorems", "12_0_competition.jsonl")
if os.path.exists(comp_file):
    store.load_jsonl(comp_file)

with open(os.path.join(ROOT, "theorems", "concept_neurons.json"), encoding="utf-8") as fh:
    data = json.load(fh)
store.concept_neurons = data["concept_neurons"]
store.neuron_edges = {}
for key, w in data.get("neuron_edges", {}).items():
    parts = key.split("|")
    if len(parts) == 2:
        store.neuron_edges[(parts[0], parts[1])] = w
store._neurons_built = True

iso_path = os.path.join(ROOT, "data", "iso_edges.json")


from numtheory_prover import parse_term, Var, Const

def _fixed_arg(self, a):
    if not isinstance(a, str):
        return a
    if "(" in a:
        return parse_term(a)
    if a.lstrip("-").isdigit():
        return Const(a)
    return Var(a)

RecursiveProver._arg = _fixed_arg
rp = RecursiveProver(store, iso_edges_path=iso_path, verbose=False)

# ---- 阶梯题 ----
CASES = [
    # L1 纯传递
    ("L1", "divides(a, c)", ["divides(a, b)", "divides(b, c)"]),
    # L2 同余传递
    ("L2", "congruent(a, c, m)", ["congruent(a, b, m)", "congruent(b, c, m)"]),
    # L3 整除线性组合
    ("L3", "divides(a, plus(b, c))", ["divides(a, b)", "divides(a, c)"]),
    # L4 同余可加
    ("L4", "congruent(plus(a,c), plus(b,d), m)",
           ["congruent(a, b, m)", "congruent(c, d, m)"]),
    # L5 同余可乘
    ("L5", "congruent(times(a,c), times(b,d), m)",
           ["congruent(a, b, m)", "congruent(c, d, m)"]),
    # L6 费马小定理直接形式
    ("L6", "congruent(power(a, p), a, p)", ["prime(p)"]),
    # L7 费马小定理互质形式
    ("L7", "congruent(power(a, minus(p,1)), 1, p)",
           ["prime(p)", "coprime(a, p)"]),
    # L8 欧拉定理
    ("L8", "congruent(power(a, phi(m)), 1, m)",
           ["coprime(a, m)", "gt(m, 1)"]),
    # L9 p²≡1 mod 24（高难）
    ("L9", "congruent(power(p,2), 1, 24)", ["prime(p)", "gt(p, 3)"]),
]

for level, goal, premises in CASES:
    print(f"\n{'='*60}")
    print(f"[{level}] goal={goal}")
    print(f"      premises={premises}")
    try:
        proof = rp.prove(goal, premises=premises, verbose=False)
    except Exception as e:
        print(f"  ❌ 异常: {e!r}")
        continue
    if proof:
        print(f"  ✅ 证明成功，{len(proof)} 步")
        for s in proof:
            print(f"      {s.strategy}  {s.subgoal}")
    else:
        print(f"  ❌ 未证明")