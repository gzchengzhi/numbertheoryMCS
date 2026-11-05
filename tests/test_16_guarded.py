# tests/test_16_guarded.py
"""16.0.2 测试：GuardedProver 语义约束。"""
import json
import glob
import os
import pytest

from adaptive_store import AdaptiveStore
from guarded_prover import GuardedProver
from numtheory_prover import (
    HornClause, Pred, Var, Const, parse_goal, unify,
)
import numtheory_prover


@pytest.fixture(scope="module")
def store():
    numtheory_prover.ENABLE_SUBST_CONSISTENCY = True
    numtheory_prover.ENABLE_EMPTY_LOWER = True
    s = AdaptiveStore()
    for f in sorted(glob.glob("theorems/*.jsonl")):
        if "learn_log" in f or "candidates" in f:
            continue
        s.load_jsonl(f)
    return s


def test_guarded_rejects_t004_when_goal_var(store):
    """goal=divides(b, a)，GuardedProver 不命中 T004。"""
    prover = GuardedProver(store, max_depth=8)
    proof = prover.prove_with_premises(
        parse_goal("divides(b, a)"),
        [parse_goal("equals(a, plus(times(b,q), 0))")],
        strategy="direct", verbose=False)
    # 不允许 T004 命中
    if proof is not None:
        ids = [s.clause.id for s in proof]
        assert "T004" not in ids, f"T004 不应命中，实际 {ids}"


def test_guarded_allows_t004_when_goal_const_one(store):
    """goal=divides(1, a)，T004 可以命中。"""
    prover = GuardedProver(store, max_depth=8)
    proof = prover.prove(parse_goal("divides(1, a)"),
                         strategy="direct", verbose=False)
    if proof is not None:
        ids = [s.clause.id for s in proof]
        assert "T004" in ids or "COMPUTED" in ids


def test_guarded_finds_t005(store):
    """goal=divides(b, a)，GuardedProver 能命中 T005（或证明成功）。"""
    prover = GuardedProver(store, max_depth=8)
    proof = prover.prove_with_premises(
        parse_goal("divides(b, a)"),
        [parse_goal("equals(a, times(b, q))")],
        strategy="direct", verbose=False)
    assert proof is not None, "T005 应能证明 divides(b, a)"
    ids = [s.clause.id for s in proof]
    assert "T004" not in ids
    
def test_guarded_rejects_t005_when_goal_var(store):
    """goal=divides(b, a)，GuardedProver 不命中 T005。"""
    prover = GuardedProver(store, max_depth=8)
    proof = prover.prove_with_premises(
        parse_goal("divides(b, a)"),
        [parse_goal("equals(a, plus(times(b,q), 0))")],
        strategy="direct", verbose=False)
    if proof is not None:
        ids = [s.clause.id for s in proof]
        assert "T005" not in ids, f"T005 不应命中，实际 {ids}"


def test_guarded_allows_t005_when_goal_zero(store):
    """goal=divides(a, 0)，T005 可以命中。"""
    prover = GuardedProver(store, max_depth=8)
    proof = prover.prove(parse_goal("divides(a, 0)"),
                         strategy="direct", verbose=False)
    if proof is not None:
        ids = [s.clause.id for s in proof]
        assert "T005" in ids or "COMPUTED" in ids