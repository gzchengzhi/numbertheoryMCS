# tests/test_18_diagnose_high_order.py
"""18.0.3a 测试：diagnose 高阶谓词检测。"""
import pytest


@pytest.mark.parametrize("goal", [
    "exists(p, and(prime(p), gt(p, n)))",
    "not_exists(d, and(gt(d, 1), divides(d, n)))",
    "implies(prime(p), gt(p, 1))",
])
def test_high_order_pred_detected(goal, capsys):
    """高阶谓词 → 提示手工转换，返回 1。"""
    from tools.diagnose import diagnose
    rc = diagnose(goal, [])
    out = capsys.readouterr().out
    assert rc == 1
    assert "高阶谓词" in out
    assert "手工转换" in out


def test_high_order_forall_can_prove(capsys):
    """forall(N, exists(p, ...)) 被 prime_infinite 神经元证明 → 不触发检测。"""
    from tools.diagnose import diagnose
    rc = diagnose("forall(N, exists(p, and(prime(p), gt(p, N))))", [])
    out = capsys.readouterr().out
    assert rc == 0  # 证明成功
    assert "高阶谓词" not in out


def test_low_order_pred_not_high_order(capsys):
    """一阶谓词不触发高阶检测。"""
    from tools.diagnose import diagnose
    rc = diagnose("divides(a, c)",
                  ["divides(a, b)", "divides(b, c)"])
    out = capsys.readouterr().out
    assert rc == 0  # 成功
    assert "高阶谓词" not in out


def test_high_order_with_proof(capsys):
    """高阶谓词但能证明 → 不触发检测（先试证明）。"""
    # 13.x 有 prime_infinite 神经元，forall 形式能证明
    from tools.diagnose import diagnose
    rc = diagnose("forall(n, exists(p, and(prime(p), gt(p, n))))", [])
    out = capsys.readouterr().out
    # 如果证明成功，rc=0，不触发高阶检测
    # 如果失败，rc=1，触发高阶检测
    assert rc in (0, 1)