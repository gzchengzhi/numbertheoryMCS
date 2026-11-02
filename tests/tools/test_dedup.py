"""验证去重脚本本身不误删。"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))

from numtheory_prover import parse_goal
from theorem_store import HornClause
from dedup_theorems import canonicalize_terms, clause_signature, literal_signature


def mk(head, body, cid="X", name="t", cat="c"):
    return HornClause(
        id=cid, name=name,
        head=parse_goal(head),
        body=[parse_goal(b) for b in body],
        category=cat,
    )


def test_alpha_equivalence():
    """变量名不同 → L2 签名相同"""
    c1 = mk("divides(a, c)", ["divides(a, b)", "divides(b, c)"], cid="T1")
    c2 = mk("divides(x, z)", ["divides(x, y)", "divides(y, z)"], cid="T2")
    assert clause_signature(c1) == clause_signature(c2)


def test_not_alpha_equivalent():
    """结构不同 → L2 签名不同"""
    c1 = mk("divides(a, c)", ["divides(a, b)", "divides(b, c)"], cid="T1")
    c2 = mk("divides(a, c)", ["divides(b, a)", "divides(b, c)"], cid="T2")
    assert clause_signature(c1) != clause_signature(c2)


def test_body_order_irrelevant():
    """body 顺序不同 → L2 签名仍相同（因为 sorted）"""
    c1 = mk("divides(a, c)", ["divides(a, b)", "divides(b, c)"], cid="T1")
    c2 = mk("divides(a, c)", ["divides(b, c)", "divides(a, b)"], cid="T2")
    assert clause_signature(c1) == clause_signature(c2)


def test_literal_signature_strict():
    """变量名不同 → L1 签名不同（保留 L1/L2 分层）"""
    c1 = mk("divides(a, c)", ["divides(a, b)", "divides(b, c)"], cid="T1")
    c2 = mk("divides(x, z)", ["divides(x, y)", "divides(y, z)"], cid="T2")
    assert literal_signature(c1) != literal_signature(c2)


def test_semantic_group_hits():
    """congruent 与 divides-diff 应被归到同一 group"""
    from dedup_rules import SEMANTIC_EQUIV
    from dedup_theorems import semantic_groups
    c1 = mk("congruent(a, b, m)", [], cid="T1")
    c2 = mk("divides(m, minus(a,b))", [], cid="T2")
    g1 = semantic_groups(c1, SEMANTIC_EQUIV)
    g2 = semantic_groups(c2, SEMANTIC_EQUIV)
    assert "congruence_divide" in g1
    assert "congruence_divide" in g2