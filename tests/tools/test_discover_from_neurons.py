"""14.0.5b: discover_from_neurons 单测（分治式）。"""
import json, os, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from adaptive_store import AdaptiveStore
from tools.discover_from_neurons import discover_from_neurons


@pytest.fixture
def store():
    s = AdaptiveStore()
    with open(os.path.join(ROOT, "theorems", "concept_neurons.json"), encoding="utf-8") as f:
        s.concept_neurons = json.load(f)["concept_neurons"]
    return s


def test_produces_depth2_4_8(store):
    cands = discover_from_neurons(store.concept_neurons, max_depth=8)
    depths = sorted(c["N"] for c in cands
                    if c["neuron_id"].startswith("NEURON::T::divides::"))
    assert depths == [2, 4, 8]


def test_depth2_shape(store):
    cands = discover_from_neurons(store.concept_neurons, max_depth=2)
    c = next(c for c in cands if c["N"] == 2)
    assert c["neuron_id"] == "NEURON::T::divides::@0-@0::depth2"
    assert c["head_pattern"] == ["divides", ["a0", "a2"]]
    assert c["lower"] == [
        ["divides", ["a0", "a1"]],
        ["divides", ["a1", "a2"]],
    ]


def test_depth4_shape(store):
    cands = discover_from_neurons(store.concept_neurons, max_depth=4)
    c = next(c for c in cands if c["N"] == 4)
    assert c["head_pattern"] == ["divides", ["a0", "a4"]]
    assert len(c["lower"]) == 4
    assert c["lower"][0] == ["divides", ["a0", "a1"]]
    assert c["lower"][3] == ["divides", ["a3", "a4"]]


def test_depth8_shape(store):
    cands = discover_from_neurons(store.concept_neurons, max_depth=8)
    c = next(c for c in cands if c["N"] == 8)
    assert c["head_pattern"] == ["divides", ["a0", "a8"]]
    assert len(c["lower"]) == 8


def test_depth4_is_two_depth2(store):
    cands = discover_from_neurons(store.concept_neurons, max_depth=4)
    c = next(c for c in cands if c["N"] == 4)
    assert c["lower"][0][0] == "NEURON::T::divides::@0-@0::depth2"
    assert c["lower"][1][0] == "NEURON::T::divides::@0-@0::depth2"
    assert c["lower"][0][1] == {"a": "a", "c": "m"}
    assert c["lower"][1][1] == {"a": "m", "c": "e"}
    assert c["head_pattern"] == ["divides", ["a", "e"]]


def test_depth8_is_two_depth4(store):
    cands = discover_from_neurons(store.concept_neurons, max_depth=8)
    c = next(c for c in cands if c["N"] == 8)
    assert c["lower"][0][0] == "NEURON::T::divides::@0-@0::depth4"
    assert c["lower"][1][0] == "NEURON::T::divides::@0-@0::depth4"
    assert c["head_pattern"] == ["divides", ["a", "i"]]


def test_idempotent_when_existing(store):
    cands1 = discover_from_neurons(store.concept_neurons, max_depth=2)
    for c in cands1:
        store.concept_neurons[c["neuron_id"]] = c
    cands2 = discover_from_neurons(store.concept_neurons, max_depth=2)
    # 已存在的 depth2 仍会产，因为 _collect_chains_for_neuron 不查 store；
    # 但 commit 层去重。这里只验证函数本身幂等（id 不重复）。
    ids = [c["neuron_id"] for c in cands2]
    assert len(ids) == len(set(ids))