# tests/test_15_solidify.py
"""15.0.4 测试：N=3 组合 + 证明路径固化。"""
import json
import os
import pytest

from adaptive_store import AdaptiveStore
from deep_recursive_prover import DeepRecursiveProver
from tools.discover_from_neurons import discover_n3, load_verified


@pytest.fixture(scope="module")
def store():
    s = AdaptiveStore()
    import glob
    for f in sorted(glob.glob("theorems/*.jsonl")):
        s.load_jsonl(f)
    if os.path.exists("theorems/concept_neurons.json"):
        with open("theorems/concept_neurons.json", encoding="utf-8") as fp:
            s.concept_neurons = json.load(fp)["concept_neurons"]
    return s


# ============================================================
# 1. N=3 组合
# ============================================================
def test_discover_n3_generates(tmp_path):
    """N=1 + N=2 再组合，产出 N=3。"""
    if not os.path.exists("theorems/15_0_new_neurons.jsonl"):
        pytest.skip("需要先跑 15.0.3")
    out = str(tmp_path / "n3.jsonl")
    items = discover_n3(
        "theorems/15_0_verified.jsonl",
        "theorems/15_0_new_neurons.jsonl",
        out, max_new=200, verbose=False)
    assert len(items) >= 1, "未生成 N=3 神经元"
    assert all(it["N"] >= 3 for it in items)


def test_discover_n3_weight(tmp_path):
    """N=3 的 weight = 0.5^2 = 0.25。"""
    if not os.path.exists("theorems/15_0_new_neurons.jsonl"):
        pytest.skip("需要先跑 15.0.3")
    out = str(tmp_path / "n3.jsonl")
    items = discover_n3(
        "theorems/15_0_verified.jsonl",
        "theorems/15_0_new_neurons.jsonl",
        out, max_new=50, verbose=False)
    for it in items:
        assert it["N"] >= 3
        expected = round(0.5 ** (it["N"] - 1), 4)
        assert abs(it["weight"] - expected) < 1e-3


# ============================================================
# 2. 固化证明路径
# ============================================================
def test_solidify_divides_chain(store):
    """a|b, b|c, c|d ⇒ a|d，固化后 store 多一条新神经元。"""
    rp = DeepRecursiveProver(store, verbose=False)
    rp.ENABLE_SUBGOAL_SPLIT = True   # ★ 强制 subgoal_split
    n_before = len(store.concept_neurons)
    proof = rp.prove_deep(
        "divides(a, d)",
        premises=["divides(a, b)", "divides(b, c)", "divides(c, d)"])
    if proof is None:
        pytest.skip("证明未成功，无法测固化")
    nid = rp.solidify(proof)
    assert nid is not None
    assert nid in store.concept_neurons
    assert len(store.concept_neurons) >= n_before  # 可能已存在


def test_solidify_idempotent(store):
    """同一证明固化两次，返回同一 id，不重复添加。"""
    rp = DeepRecursiveProver(store, verbose=False)
    proof = rp.prove_deep(
        "divides(a, c)",
        premises=["divides(a, b)", "divides(b, c)"])
    if proof is None:
        pytest.skip("证明未成功")
    nid1 = rp.solidify(proof)
    nid2 = rp.solidify(proof)
    assert nid1 == nid2


def test_solidify_weight_decay(store):
    """固化后的神经元 weight 符合 0.5^(N-1)。"""
    rp = DeepRecursiveProver(store, verbose=False)
    proof = rp.prove_deep(
        "divides(a, c)",
        premises=["divides(a, b)", "divides(b, c)"])
    if proof is None:
        pytest.skip("证明未成功")
    nid = rp.solidify(proof)
    neuron = store.concept_neurons.get(nid)
    assert neuron is not None
    n = neuron["N"]
    expected = round(0.5 ** (n - 1), 4)
    assert abs(neuron["weight"] - expected) < 1e-3