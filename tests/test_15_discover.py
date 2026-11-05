# tests/test_15_discover.py
"""15.0.3 测试：discover_from_neurons。"""
import json
import os
import pytest

from tools.discover_from_neurons import (
    load_verified, dict_to_clause, NeuronComposer, discover,
)


@pytest.fixture(scope="module")
def verified():
    if not os.path.exists("theorems/15_0_verified.jsonl"):
        pytest.skip("15_0_verified.jsonl 不存在，先跑 15.0.2")
    return load_verified("theorems/15_0_verified.jsonl")


# ============================================================
# 1. 加载
# ============================================================
def test_load_verified(verified):
    assert len(verified) > 0
    # 每条有 N
    assert all("N" in r for r in verified)


def test_dict_to_clause(verified):
    rec = verified[0]
    c = dict_to_clause(rec)
    assert c is not None
    assert c.head is not None


# ============================================================
# 2. 组合
# ============================================================
def test_compose_generates_new(verified):
    """两两组合应生成至少 1 条新神经元。"""
    composer = NeuronComposer(verified, max_new=500, verbose=False)
    items = composer.compose()
    assert len(items) >= 1, "未生成任何新神经元"
    # 每条 N >= 2
    assert all(it["N"] >= 2 for it in items)
    # 每条有 composed_from
    assert all(len(it["composed_from"]) == 2 for it in items)


def test_compose_n_ge_2(verified):
    """新神经元 N 必须 >= 2（父 N + 1）。"""
    composer = NeuronComposer(verified, max_new=200, verbose=False)
    items = composer.compose()
    for it in items:
        assert it["N"] >= 2


def test_compose_weight_decay(verified):
    """weight = 0.5^(N-1)。"""
    composer = NeuronComposer(verified, max_new=50, verbose=False)
    items = composer.compose()
    for it in items:
        expected = round(0.5 ** (it["N"] - 1), 4)
        assert abs(it["weight"] - expected) < 1e-3


def test_compose_no_self(verified):
    """新神经元不能和父神经元完全相同。"""
    composer = NeuronComposer(verified, max_new=100, verbose=False)
    items = composer.compose()
    parent_sigs = set()
    for r in verified:
        parent_sigs.add((r["head"], tuple(sorted(r["body"]))))
    for it in items:
        sig = (it["head"], tuple(sorted(it["body"])))
        assert sig not in parent_sigs, f"{it['id']} 与父神经元重复"


def test_compose_max_limit(verified):
    """max_new 限制生效。"""
    composer = NeuronComposer(verified, max_new=10, verbose=False)
    items = composer.compose()
    assert len(items) <= 10


def test_compose_structure_pass(verified):
    """每条新神经元必须过 verify_by_structure。"""
    from tools.verify_neuron import verify_by_structure
    composer = NeuronComposer(verified, max_new=100, verbose=False)
    items = composer.compose()
    for it in items:
        c = dict_to_clause(it)
        assert verify_by_structure(c) is True, f"{it['id']} structure 失败"


# ============================================================
# 3. 端到端
# ============================================================
def test_discover_end_to_end(tmp_path, verified):
    """discover() 写文件。"""
    out = str(tmp_path / "new.jsonl")
    items = discover("theorems/15_0_verified.jsonl", out, max_new=50,
                     verbose=False)
    assert len(items) >= 1
    assert os.path.exists(out)
    with open(out, encoding="utf-8") as f:
        lines = [json.loads(l) for l in f if l.strip()]
    assert len(lines) == len(items)