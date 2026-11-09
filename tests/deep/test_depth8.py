"""14.0.5e: D002 8 步传递链走 depth8。"""
import pytest
from tests.deep._helpers import get_case
pytestmark = pytest.mark.xfail(
    reason="14.0.5 的 DeepRecursiveProver 依赖 RecursiveProver._match_lower，"
           "subst 在 @0-@1 层被污染（divides(b,c) unify divides(a,b) 得 b:a,c:a），"
           "14.0.6 用独立 TriangleProver 重做",
    strict=False)

def test_d002_depth8_chain(deep_rp, deep_cases):
    case = get_case(deep_cases, "D002")
    proof = deep_rp.prove(case["goal"], premises=case["premises"], verbose=False)
    assert proof is not None, "D002 未证明"
    strategies = [st.strategy for st in proof]
    assert any("::depth8" in st for st in strategies), \
        f"D002 期望 depth8 神经元，实际 {strategies}"


def test_d002_recursion_depth_within_8(deep_rp, deep_cases):
    case = get_case(deep_cases, "D002")
    proof = deep_rp.prove(case["goal"], premises=case["premises"], verbose=False)
    assert proof is not None
    assert all(st.depth <= 8 for st in proof), \
        f"D002 递归深度超限：{[st.depth for st in proof]}"


def test_d002_does_not_use_depth9(deep_rp, deep_cases):
    case = get_case(deep_cases, "D002")
    proof = deep_rp.prove(case["goal"], premises=case["premises"], verbose=False)
    assert proof is not None
    strategies = [st.strategy for st in proof]
    assert not any("::depth9" in st for st in strategies)