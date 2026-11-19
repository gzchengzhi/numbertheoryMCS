# tests/test_20_erdos_straus_p1_mod24.py
import pytest
from tools.erdos_straus_p1_mod24_symbolic import (
    branch_succeeds, compute_failure_set, density_zero_theorem_record,
)


def test_branch_succeeds_real_check():
    """验证 branch_succeeds 是真实的 d 存在性检查。"""
    # p=97, r=23 是已知的失败案例（N 含非剩余 5，但 d 不存在）
    assert branch_succeeds(97, 23) is False
    # p=73, r=7 是已知的成功案例
    assert branch_succeeds(73, 7) is True


def test_failure_set_actual_r3():
    """实测 F_3 = [1]。"""
    assert compute_failure_set(3) == [1]


def test_failure_set_actual_r7():
    """实测 F_7 = [1, 2, 4]。"""
    assert compute_failure_set(7) == [1, 2, 4]


def test_failure_set_actual_r11():
    """实测 F_11 = [1, 2, 3, 4, 5, 6, 9]。"""
    assert compute_failure_set(11) == [1, 2, 3, 4, 5, 6, 9]


def test_failure_set_actual_r23():
    """实测 F_23 = [1, 2, 3, 4, 5, 6, 8, 9, 12, 13, 14, 16, 18]。"""
    assert compute_failure_set(23) == [1, 2, 3, 4, 5, 6, 8, 9, 12, 13, 14, 16, 18]


def test_failure_rate_lt_one():
    """20.0.3 前提：每个 r 的失败率 < 1（实测 |F_r| < r-1）。"""
    for r in [3, 7, 11, 23]:
        F = compute_failure_set(r)
        assert len(F) < r - 1, f"r={r}: |F_r|={len(F)} >= r-1={r-1}"


def test_density_zero_record():
    """20.0.3：大筛密度 0 记录存在，且不声称全称。"""
    rec = density_zero_theorem_record()
    assert rec["neuron"].startswith("NEURON::S::uncovered_density_zero")
    assert "不声称例外集为空" in rec["note"]