"""14.0.5e: D003 同余传递链，5e 默认只开 divides，标 xfail 占位。"""
import pytest
from tests.deep._helpers import get_case


@pytest.mark.xfail(reason="5e 默认 only_predicates={divides}，14.0.6 分层扩展时开 congruent",
                   strict=True)
def test_d003_congruent_chain(deep_rp, deep_cases):
    case = get_case(deep_cases, "D003")
    proof = deep_rp.prove(case["goal"], premises=case["premises"], verbose=False)
    assert proof is not None
    strategies = [st.strategy for st in proof]
    assert any("::depth4" in st for st in strategies)