# tests/bench/test_11_recursive_firing.py
import glob, os
import pytest
from adaptive_store import AdaptiveStore
from recursive_prover import RecursiveProver

CASES = [
    ("equals_chain", "equals(r1, r2)",
     ["equals(a, plus(times(b,q1),r1))",
      "equals(a, plus(times(b,q2),r2))",
      "lt(r2, b)"]),
]

def _load_store():
    store = AdaptiveStore()
    if os.path.exists("theorems.jsonl"):
        store.load_jsonl("theorems.jsonl")
    for p in sorted(glob.glob("theorems/*.jsonl")):
        store.load_jsonl(p)
    store.load_weights()
    store.load_dependency_records()
    store.load_neurons("theorems/concept_neurons.json")
    return store

@pytest.mark.parametrize("case_id,goal_str,premises", CASES)
def test_recursive_firing(case_id, goal_str, premises):
    store = _load_store()
    rp = RecursiveProver(store, verbose=True)
    result = rp.prove(goal_str, premises=premises, verbose=True)
    print(f"\n[recursive/{case_id}] result={result}")
    assert result is not None, f"递归点火 + 回退都没解出 {case_id}"
    strategies = [s.strategy for s in result]
    assert any("NEURON::T::equals::@1-@1" in s for s in strategies), \
        f"未命中外层嵌套神经元: {strategies}"