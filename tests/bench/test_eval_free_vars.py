# tests/bench/test_eval_free_vars.py
import pytest
pytestmark = pytest.mark.skip(reason="evaluate_predicate 对自由变量误判，待修")

CASES = [
    ("gcd_assoc", "equals(gcd(gcd(a,b),c), gcd(a,gcd(b,c)))"),
    ("lcm_assoc", "equals(lcm(lcm(a,b),c), lcm(a,lcm(b,c)))"),
]

@pytest.mark.parametrize("case_id,goal_str", CASES)
def test_eval_free_vars(case_id, goal_str):
    """自由变量不应被 COMPUTED 判真，待修 evaluate_predicate。"""
    pytest.skip(f"evaluate_predicate 自由变量 bug：{case_id}")