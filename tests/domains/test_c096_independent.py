# tests/domains/test_c096_independent.py
"""C096 独立测试：从 0 构造勾股数参数化的证明。"""
import sys, os, json, glob
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from adaptive_store import AdaptiveStore
from recursive_prover import RecursiveProver

import numtheory_prover
numtheory_prover.ENABLE_SUBST_CONSISTENCY = True
numtheory_prover.ENABLE_EMPTY_LOWER = True


@pytest.fixture
def c096_rp():
    """独立构造 C096 的 store：主库 + C096 独立定理。"""
    store = AdaptiveStore()
    # 主库 theorems
    for f in sorted(glob.glob("theorems/*.jsonl")):
        base = os.path.basename(f)
        if "learn_log" in base or "candidates" in base:
            continue
        store.load_jsonl(f)
    # 主库神经元（不含 S::pythagorean）
    with open("theorems/concept_neurons.json", encoding="utf-8") as fh:
        data = json.load(fh)
    neurons = dict(data["concept_neurons"])
    # 删除 S::pythagorean（独立测试，不用旧的）
    neurons.pop("NEURON::S::pythagorean<-exists::arity=3", None)
    store.concept_neurons = neurons
    store._neurons_built = True
    if hasattr(store, "_head_index"):
        del store._head_index
    if hasattr(store, "_clause_head_index"):
        del store._clause_head_index
    # 加载 domains
    from concept_domain import DomainRegistry
    reg = DomainRegistry("domains")
    reg.load_all_into(store)
    # 加载 C096 独立神经元
    with open("theorems/c096_pythagorean_neurons.json", encoding="utf-8") as fh:
        c096_data = json.load(fh)
    for nid, n in c096_data["concept_neurons"].items():
        store.concept_neurons[nid] = n
    if hasattr(store, "_head_index"):
        del store._head_index
    return RecursiveProver(store, iso_edges_path="data/iso_edges.json")


def test_c096_pythagorean(c096_rp):
    goal = "exists(m, exists(n, and(gt(m,n), coprime(m,n), equals(a, minus(power(m,2),power(n,2))), equals(b, times(2,times(m,n))), equals(c, plus(power(m,2),power(n,2))))))"
    premises = [
        "equals(plus(power(a,2),power(b,2)), power(c,2))",
        "gt(a,0)", "gt(b,0)", "gt(c,0)",
    ]
    proof = c096_rp.prove(goal, premises=premises, verbose=True)
    print(f"\n=== C096 PROOF ===")
    print(proof)
    assert proof is not None, "C096 未证明"
    print(f"strategies: {[s.strategy for s in proof]}")