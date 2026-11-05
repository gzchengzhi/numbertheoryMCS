# tests/test_16_semantic.py
"""16.0.1 测试：semantic_guard。"""
import pytest
from numtheory_prover import parse_goal, unify, Pred, Var, Const
from semantic_guard import check_subst_semantic


def test_t004_rejected():
    """T004 divides(1, a) vs divides(b, a) → {b: 1} → 拒绝。"""
    head = parse_goal("divides(1, a)")
    goal = parse_goal("divides(b, a)")
    subst = unify(head, goal, {})
    assert subst is not None
    assert check_subst_semantic(goal, head, subst) is False


def test_t005_allowed():
    """T005 divides(x, y) vs divides(b, a) → {x: b, y: a} → 允许。"""
    head = parse_goal("divides(x, y)")
    goal = parse_goal("divides(b, a)")
    subst = unify(head, goal, {})
    assert subst is not None
    assert check_subst_semantic(goal, head, subst) is True


def test_divides_one_allowed():
    """divides(1, a) vs divides(1, a) → {} → 允许。"""
    head = parse_goal("divides(1, a)")
    goal = parse_goal("divides(1, a)")
    subst = unify(head, goal, {})
    assert subst is not None
    assert check_subst_semantic(goal, head, subst) is True


def test_var_var_binding_allowed():
    """head Var 绑 goal Var → 允许。"""
    head = parse_goal("divides(a, b)")
    goal = parse_goal("divides(x, y)")
    subst = unify(head, goal, {})
    assert subst is not None
    assert check_subst_semantic(goal, head, subst) is True


def test_const_const_match_allowed():
    """head Const 和 goal Const 相同 → 允许。"""
    head = parse_goal("divides(2, a)")
    goal = parse_goal("divides(2, b)")
    subst = unify(head, goal, {})
    assert subst is not None
    assert check_subst_semantic(goal, head, subst) is True


def test_const_mismatch_rejected():
    """head divides(2, a) vs goal divides(3, a) → unify 失败，check 不相关。"""
    head = parse_goal("divides(2, a)")
    goal = parse_goal("divides(3, a)")
    subst = unify(head, goal, {})
    assert subst is None  # unify 已经失败，check 不会被调用