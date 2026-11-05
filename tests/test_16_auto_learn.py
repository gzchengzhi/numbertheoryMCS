
# tests/test_16_auto_learn.py
"""16.0.3a 测试：失败驱动的候选生成（不自动合入）。"""
import json
import glob
import os
import pytest

from adaptive_store import AdaptiveStore
from tools.learn_from_failure import (
    suggest_candidates, generate_candidates, _parse_pattern,
    _is_valid_candidate, collect_fallbacks,
)


# ============================================================
# Fixture
# ============================================================
@pytest.fixture(scope="module")
def store():
    """空 store，只加载 concept_neurons.json（不加载定理库）。"""
    s = AdaptiveStore()
    path = "theorems/concept_neurons.json"
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        s.concept_neurons = data.get("concept_neurons", {})
    return s


# ============================================================
# 1. suggest_candidates：基本生成
# ============================================================
def test_suggest_basic(store):
    """单条失败题 → 1 条候选。"""
    cands = suggest_candidates(
        "divides(b, a)",
        ["equals(a, plus(times(b,q), 0))"],
        store)
    assert len(cands) == 1
    c = cands[0]
    assert c["neuron_id"].startswith("NEURON::S::divides<-equals")
    assert c["head_pattern"] == ["divides", ["b", "a"]]
    assert c["lower"] == [["equals", ["a", "plus(times(b,q), 0)"]]]
    assert c["source"] == "AUTO"


def test_suggest_multi_premises(store):
    """多前提题 → 1 条候选，lower 有 3 条。"""
    cands = suggest_candidates(
        "congruent(a, b, div(m,d))",
        ["congruent(times(d,a), times(d,b), m)",
         "gt(d, 0)",
         "divides(d, m)"],
        store)
    assert len(cands) == 1
    c = cands[0]
    assert c["head_pattern"] == ["congruent", ["a", "b", "div(m,d)"]]
    assert len(c["lower"]) == 3
    assert c["neuron_id"].startswith(
        "NEURON::S::congruent<-congruent+divides+gt")


# ============================================================
# 2. suggest_candidates：过滤规则
# ============================================================
def test_suggest_empty_premises(store):
    """premises 为空 → 空列表（事实型不需要神经元）。"""
    cands = suggest_candidates("prime(2)", [], store)
    assert cands == []


def test_suggest_dedup(store):
    """store 里已有相同 head_pattern + lower → 空列表。"""
    # 先手动加一条
    nid = "NEURON::S::divides<-equals::arity=auto"
    store.concept_neurons[nid] = {
        "neuron_id": nid,
        "type": "single",
        "lower": [["equals", ["a", "plus(times(b,q), 0)"]]],
        "mediator": None,
        "anchor": None,
        "head_pattern": ["divides", ["b", "a"]],
        "N": 1,
        "weight": 1.0,
        "instances": [],
    }
    try:
        cands = suggest_candidates(
            "divides(b, a)",
            ["equals(a, plus(times(b,q), 0))"],
            store)
        assert cands == []
    finally:
        store.concept_neurons.pop(nid, None)


# ============================================================
# 3. _parse_pattern：嵌套括号正确性
# ============================================================
def test_parse_pattern_nested():
    """嵌套括号的 arg 完整保留。"""
    p = _parse_pattern("equals(a, plus(times(b,q), 0))")
    assert p == ["equals", ["a", "plus(times(b,q), 0)"]]


def test_parse_pattern_div():
    """div(m,d) 的右括号不丢。"""
    p = _parse_pattern("congruent(a, b, div(m,d))")
    assert p == ["congruent", ["a", "b", "div(m,d)"]]


def test_parse_pattern_no_args():
    """无参数谓词。"""
    p = _parse_pattern("prime_infinite")
    assert p == ["prime_infinite", []]


# ============================================================
# 4. _is_valid_candidate：过滤规则
# ============================================================
def test_invalid_sympy():
    """used_clauses 含 SYMPY → 无效。"""
    fb = {"id": "X", "goal": "prime(2)", "premises": ["gt(2,0)"],
          "used_clauses": ["SYMPY"], "strategies": ["sympy"]}
    assert _is_valid_candidate(fb) is False


def test_invalid_computed():
    """used_clauses 含 COMPUTED → 无效。"""
    fb = {"id": "X", "goal": "nonzero(1)", "premises": ["gt(1,0)"],
          "used_clauses": ["COMPUTED"], "strategies": ["direct"]}
    assert _is_valid_candidate(fb) is False


def test_invalid_all_neuron_to_thm():
    """used_clauses 全是 NEURON_TO_THM → 无效（15.0.2 已覆盖）。"""
    fb = {"id": "X", "goal": "equals(a, b)",
          "premises": ["equals(a, b)"],
          "used_clauses": ["NEURON_TO_THM::NEURON::S::equals<-norm::arity=2"],
          "strategies": ["direct"]}
    assert _is_valid_candidate(fb) is False


def test_valid_normal():
    """used_clauses 是 T0xx → 有效。"""
    fb = {"id": "X", "goal": "divides(b, a)",
          "premises": ["equals(a, times(b,q))"],
          "used_clauses": ["T025"], "strategies": ["direct"]}
    assert _is_valid_candidate(fb) is True


# ============================================================
# 5. generate_candidates：批量生成 + 格式
# ============================================================
def test_generate_candidates_format():
    """generate_candidates 返回的候选格式正确（head_pattern/lower 是 list）。"""
    fbs = [
        {"id": "X1", "goal": "divides(b, a)",
         "premises": ["equals(a, plus(times(b,q), 0))"],
         "used_clauses": ["T025"], "strategies": ["direct"]},
        {"id": "X2", "goal": "prime(2)",
         "premises": ["gt(2, 0)"],
         "used_clauses": ["SYMPY"], "strategies": ["sympy"]},  # 跳过
    ]
    cands = generate_candidates(fbs)
    assert len(cands) == 1
    c = cands[0]
    assert isinstance(c["head_pattern"], list)
    assert isinstance(c["lower"], list)
    assert isinstance(c["lower"][0], list)
    assert c["source"] == "X1"


def test_generate_candidates_empty():
    """空 fallback 列表 → 空候选。"""
    assert generate_candidates([]) == []