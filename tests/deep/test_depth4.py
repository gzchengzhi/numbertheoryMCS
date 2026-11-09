"""14.0.5e: D001 4 步传递链走 depth4。"""
import pytest
from tests.deep._helpers import get_case
pytestmark = pytest.mark.xfail(
    reason="14.0.5 的 DeepRecursiveProver 依赖 RecursiveProver._match_lower，"
           "subst 在 @0-@1 层被污染（divides(b,c) unify divides(a,b) 得 b:a,c:a），"
           "14.0.6 用独立 TriangleProver 重做",
    strict=False)

def test_d001_depth4_chain(deep_rp, deep_cases):
    case = get_case(deep_cases, "D001")
    proof = deep_rp.prove(case["goal"], premises=case["premises"], verbose=False)
    assert proof is not None, "D001 未证明"
    strategies = [st.strategy for st in proof]
    assert any("::depth4" in st for st in strategies), \
        f"D001 期望 depth4 神经元，实际 {strategies}"


def test_d001_does_not_use_depth8(deep_rp, deep_cases):
    """D001 是 4 步链，不应该误用 depth8。"""
    case = get_case(deep_cases, "D001")
    proof = deep_rp.prove(case["goal"], premises=case["premises"], verbose=False)
    assert proof is not None
    strategies = [st.strategy for st in proof]
    assert not any("::depth8" in st for st in strategies), \
        f"D001 误用 depth8：{strategies}"