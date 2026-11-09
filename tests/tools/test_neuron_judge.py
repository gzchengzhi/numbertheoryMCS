"""14.0.5c: neuron_judge 单测。"""
import json, os, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from adaptive_store import AdaptiveStore
from tools.neuron_judge import judge as neuron_judge
from tools.learn_12_0 import judge as rules_judge


@pytest.fixture
def store():
    s = AdaptiveStore()
    with open(os.path.join(ROOT, "theorems", "concept_neurons.json"), encoding="utf-8") as f:
        s.concept_neurons = json.load(f)["concept_neurons"]
    return s


def test_non_neuron_non_n2_equals_rules(store):
    """非 NEURON:: 非 N>=2 且有 neuron_id 的输入，逐字节等于 learn_12_0.judge。"""
    checked = 0
    for nid, n in store.concept_neurons.items():
        if "neuron_id" not in n:
            continue   # learn_12_0.judge 要求 neuron_id，缺字段两者都抛 KeyError，跳过
        lower = n.get("lower") or []
        has_neuron = any(
            (isinstance(l, str) and l.startswith("NEURON::")) or
            (isinstance(l, (list, tuple)) and l and isinstance(l[0], str)
             and l[0].startswith("NEURON::"))
            for l in lower
        )
        if has_neuron or int(n.get("N", 1)) >= 2:
            continue
        rec = dict(n)
        assert neuron_judge(rec) == rules_judge(rec), nid
        checked += 1
    assert checked > 0, "没有可对比的样本"


def test_neuron_lower_overrides_drop():
    """lower 含 NEURON:: 但规则 drop -> 覆盖为 keep。"""
    rec = {
        "neuron_id": "NEURON::T::divides::@0-@0::depth2",
        "type": "transitive",
        "lower": [
            ["NEURON::T::divides::@0-@1::arity=2", {"a": "a", "c": "b"}],
            ["divides", ["b", "c"]],
        ],
        "head_pattern": ["divides", ["a", "c"]],
        "N": 2,
    }
    # 规则 judge 对 T 型会 keep，这里构造一个规则会 drop 的场景：
    # 把 type 改成 single，lower 含 NEURON::，规则可能 drop（weak_single_hp_none）
    rec_single = dict(rec)
    rec_single["type"] = "single"
    rec_single["head_pattern"] = None
    decision, reason = neuron_judge(rec_single)
    assert decision == "keep"
    assert reason in ("neuron_lower_override", "n_ge_2_override")


def test_n_ge_2_overrides_drop():
    """N>=2 但规则 drop -> 覆盖为 keep。"""
    rec = {
        "neuron_id": "NEURON::S::foo::depth3",
        "type": "single",
        "lower": [],
        "head_pattern": None,
        "N": 3,
    }
    # lower 为空，规则会 drop（lower_empty），但 N>=2 覆盖
    decision, reason = neuron_judge(rec)
    assert decision == "keep"
    assert reason == "n_ge_2_override"


def test_bad_pred_still_drop_unless_override():
    """lower 含 PRED_BAD 但无 NEURON:: 且 N==1 -> 仍 drop。"""
    rec = {
        "neuron_id": "NEURON::S::exists<-foo::arity=1",
        "type": "single",
        "lower": [["exists", ["x", "P(x)"]]],
        "head_pattern": None,
        "N": 1,
    }
    decision, reason = neuron_judge(rec)
    assert decision == "drop"
    assert "bad_pred" in reason