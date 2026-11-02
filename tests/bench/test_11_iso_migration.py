# tests/bench/test_11_iso_migration.py
import glob, os
import pytest
from adaptive_store import AdaptiveStore
from recursive_prover import RecursiveProver

CASES_ISO = [
    # 第1对边：divides 传递 → congruent 传递（lower_map 把 congruent lower 映射到 divides）
    ("iso_divides_to_congruent",
     "congruent(a, c, m)",
     ["divides(m, minus(a,b))", "divides(m, minus(b,c))"]),
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

@pytest.mark.parametrize("case_id,goal_str,premises", CASES_ISO)
def test_iso_migration(case_id, goal_str, premises):
    store = _load_store()
    rp = RecursiveProver(store, iso_edges_path="data/iso_edges.json", verbose=True)
    result = rp.prove(goal_str, premises=premises, verbose=True)
    print(f"\n[iso/{case_id}] result={result}")
    assert result is not None, f"同构迁移未命中 {case_id}"
    strategies = [s.strategy for s in result]
    assert any("iso:" in s for s in strategies), \
        f"未走同构迁移路径: {strategies}"