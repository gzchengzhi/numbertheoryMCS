# tests/test_15_neuron_to_theorem.py
"""15.0.2 测试：neuron_to_theorem + verify_neuron。"""
import json
import os
import pytest

from adaptive_store import AdaptiveStore
from numtheory_prover import HornClause, Pred, Var, Const
from tools.neuron_to_theorem import (
    NeuronToTheorem, convert_file, load_neurons,
)
from tools.verify_neuron import (
    verify_clause, verify_all, verify_by_structure,
)


@pytest.fixture(scope="module")
def neurons():
    return load_neurons("theorems/concept_neurons.json")


@pytest.fixture(scope="module")
def store():
    return AdaptiveStore()


# ============================================================
# 1. 转换：有 head_pattern 的神经元转成定理
# ============================================================
def test_convert_transitive(neurons):
    """传递型神经元 NEURON::T::divides::@0-@1::arity=2 → HornClause。"""
    conv = NeuronToTheorem(neurons)
    c = conv.convert("NEURON::T::divides::@0-@1::arity=2")
    assert c is not None
    assert c.head.name == "divides"
    assert len(c.body) == 2
    assert c.body[0].name == "divides"
    assert c.body[1].name == "divides"
    assert all(type(a).__name__ == "Var" for a in c.head.args)


def test_convert_shared_param_no_head(neurons):
    """无 head_pattern 的 SP 神经元跳过（anchor 隐含 head，不能独立成定理）。"""
    conv = NeuronToTheorem(neurons)
    c = conv.convert("NEURON::SP::divides<-divides+divides::arity=2")
    assert c is None


def test_convert_shared_param_with_head(neurons):
    """有 head_pattern 的 SP 神经元可转。"""
    conv = NeuronToTheorem(neurons)
    c = conv.convert("NEURON::SP::congruent<-coprime+gt::arity=3")
    assert c is not None
    assert c.head.name == "congruent"
    assert len(c.body) == 2


def test_convert_skip_no_head(neurons):
    """head_pattern is None 的神经元跳过。"""
    conv = NeuronToTheorem(neurons)
    c = conv.convert("NEURON::S::divides<-nonzero::arity=2")
    assert c is None


def test_convert_skip_nested_neuron_unconvertible(neurons):
    """lower 里有可转的 NEURON::xxx → 整条可转。"""
    conv = NeuronToTheorem(neurons)
    c = conv.convert("NEURON::T::equals::@1-@1::arity=2")
    assert c is not None
    assert c.head.name == "equals"


def test_convert_all_count(neurons):
    """转换数量：有 head_pattern 的神经元数。"""
    conv = NeuronToTheorem(neurons)
    all_clauses = conv.convert_all()
    n_with_head = sum(
        1 for n in neurons.values() if n.get("head_pattern") is not None)
    assert len(all_clauses) > 0
    assert len(all_clauses) <= n_with_head
    assert len(all_clauses) >= 10


# ============================================================
# 2. 验证：sympy + structure 双重验证
# ============================================================
def test_verify_divides_transitive(neurons, store):
    """divides 传递性：含 Var，sympy 不判，structure 兜底。"""
    conv = NeuronToTheorem(neurons)
    c = conv.convert("NEURON::T::divides::@0-@1::arity=2")
    status, reason = verify_clause(c, store)
    assert status == "verified", f"reason={reason}"
    assert reason == "structure"


def test_verify_congruent_transitive(neurons, store):
    """congruent 传递性：含 Var，structure 兜底。"""
    conv = NeuronToTheorem(neurons)
    c = conv.convert("NEURON::T::congruent::@0-@1::arity=3")
    status, reason = verify_clause(c, store)
    assert status == "verified", f"reason={reason}"
    assert reason == "structure"


def test_verify_skip_no_head(neurons, store):
    """无 head 的神经元不参与验证。"""
    conv = NeuronToTheorem(neurons)
    c = conv.convert("NEURON::S::divides<-nonzero::arity=2")
    assert c is None


def test_verify_all_buckets(neurons, store):
    """批量验证：至少 80% verified（15.0.2 目标）。"""
    conv = NeuronToTheorem(neurons)
    clauses = conv.convert_all()
    buckets = verify_all(clauses)
    total = sum(len(v) for v in buckets.values())
    assert total == len(clauses)
    assert len(buckets["verified"]) >= len(clauses) * 0.8, (
        f"verified={len(buckets['verified'])}/{len(clauses)}")


# ============================================================
# 3. structure 规则本身（不依赖 json，构造 HornClause 直接测）
# ============================================================
def test_structure_rejects_self_ref():
    """head 和 body 完全相同 → 自引用，structure 返回 False。"""
    p = Pred("divides", (Var("a"), Var("b")))
    clause = HornClause(
        id="SELF_REF", name="self ref",
        head=p, body=[p], category="test")
    assert verify_by_structure(clause) is False


def test_structure_accepts_extra_param():
    """head 有 body 没有的额外自由参数（如 add_same 的 c）→ 合法。"""
    # congruent(plus(a,c), plus(b,c), m) :- congruent(a,b,m)
    head = Pred("congruent", (
        Const("plus", (Var("a"), Var("c"))),
        Const("plus", (Var("b"), Var("c"))),
        Var("m"),
    ))
    body = [Pred("congruent", (Var("a"), Var("b"), Var("m")))]
    clause = HornClause(
        id="ADD_SAME", name="add same",
        head=head, body=body, category="test")
    assert verify_by_structure(clause) is True


def test_structure_rejects_no_overlap():
    """head 和 body 的自由 Var 完全无交集 → 凭空断言，False。"""
    head = Pred("divides", (Var("x"), Var("y")))
    body = [Pred("prime", (Var("p"),))]
    clause = HornClause(
        id="NO_OVERLAP", name="no overlap",
        head=head, body=body, category="test")
    assert verify_by_structure(clause) is False


def test_structure_binder_not_free():
    """exists(p, ...) 的 p 是绑定变量，不计入自由 Var。"""
    # head = exists(p, divides(p, n))
    # body = [gt(n, 1)]
    # 自由 Var：head 只有 n，body 只有 n → 有交集，structure 通过
    inner = Pred("divides", (Var("p"), Var("n")))
    head = Pred("exists", (Var("p"), inner))
    body = [Pred("gt", (Var("n"), Const("1")))]
    clause = HornClause(
        id="BINDER", name="binder",
        head=head, body=body, category="test")
    assert verify_by_structure(clause) is True