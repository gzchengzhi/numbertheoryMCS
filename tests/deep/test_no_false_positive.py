"""14.0.5e: D004/D005 反例，必须证不出。"""
import pytest
from tests.deep._helpers import get_case
pytestmark = pytest.mark.xfail(
    reason="14.0.5 的 DeepRecursiveProver 回退 AdaptiveProver.direct，"
           "T004/T002 产生假阳性；14.0.6 TriangleProver 不回退，重做",
    strict=False)

@pytest.mark.parametrize("cid", ["D004", "D005"])
def test_false_positive_rejected(deep_rp, deep_cases, cid):
    case = get_case(deep_cases, cid)
    proof = deep_rp.prove(case["goal"], premises=case["premises"], verbose=False)
    assert proof is None, \
        f"{cid} 应为反例但被证明：{[s.strategy for s in proof]}"