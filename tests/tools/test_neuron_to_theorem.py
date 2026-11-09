"""14.0.5a: neuron_to_theorem 单测。用现成的 NEURON::T::divides::@0-@1::arity=2。"""
import json, os, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from adaptive_store import AdaptiveStore
from tools.neuron_to_theorem import neuron_to_clause, neurons_to_clauses


@pytest.fixture
def store():
    s = AdaptiveStore()
    with open(os.path.join(ROOT, "theorems", "concept_neurons.json"), encoding="utf-8") as f:
        s.concept_neurons = json.load(f)["concept_neurons"]
    return s


def test_depth1_neuron_to_clause(store):
    nid = "NEURON::T::divides::@0-@1::arity=2"
    n = store.concept_neurons[nid]
    c = neuron_to_clause(n, store)
    assert c is not None
    assert c.id == f"DERIVED::{nid}"
    assert str(c.head) == "divides(a,c)"
    assert [str(b) for b in c.body] == ["divides(a,b)", "divides(b,c)"]
    assert c.provenance["derived_from"] == [nid]
    assert c.provenance["N"] == 1


def test_neuron_without_head_pattern_returns_none(store):
    # 找一个 head_pattern=None 的神经元
    nid = next(nid for nid, n in store.concept_neurons.items()
               if n.get("head_pattern") is None)
    n = store.concept_neurons[nid]
    assert neuron_to_clause(n, store) is None


def test_batch_skips_invalid(store):
    clauses = neurons_to_clauses(store.concept_neurons, store)
    # 至少能转出 depth1 那条
    assert any(c.id.endswith("NEURON::T::divides::@0-@1::arity=2") for c in clauses)
    # 全部都有 provenance
    assert all(hasattr(c, "provenance") for c in clauses)


def test_mapping_applied_to_sub_neuron(store):
    """构造一个 depth2 神经元，验证 mapping 生效。"""
    depth2 = {
        "neuron_id": "NEURON::T::divides::@0-@0::depth2",
        "type": "transitive",
        "lower": [
            ["NEURON::T::divides::@0-@1::arity=2", {"a": "a", "c": "b"}],
            ["divides", ["b", "c"]],
        ],
        "head_pattern": ["divides", ["a", "c"]],
        "N": 2,
        "weight": 1.0,
    }
    c = neuron_to_clause(depth2, store)
    assert c is not None
    assert str(c.head) == "divides(a,c)"
    # 子神经元 head_pattern 是 divides(a,c)，mapping a→a, c→b → divides(a,b)
    assert [str(b) for b in c.body] == ["divides(a,b)", "divides(b,c)"]
    assert c.provenance["N"] == 2