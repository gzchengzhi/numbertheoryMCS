# tests/test_19_erdos_straus.py
"""19.0.2 Erdős–Straus 条件归约测试。

覆盖：
  - Layer 1：EP 实例验证（人手给的已知解）
  - Layer 2：归约恒等式（P ⟹ Q 的实例验证，笛卡尔积）
  - Layer 3：n ≡ 0 (mod 4) 特例（4/(4k) = 1/(2k)+1/(3k)+1/(6k)）
  - 文档断言：EP_PRIME_BOUND == 10^17，SYSTEM_PRIME_BOUND == 100
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import sympy
import pytest

from tools.erdos_straus import (
    EP_PRIME_BOUND,
    SYSTEM_PRIME_BOUND,
    SYSTEM_K_BOUND,
    verify_ep_instance,
    verify_reduction_identity,
    verify_reduction_from_ep,
    verify_mod4_zero,
    KNOWN_EP_INSTANCES,
    get_valid_known_instances,
)


# ============================================================
# 0. 文档常量
# ============================================================
def test_ep_bound_documented():
    assert EP_PRIME_BOUND == 10**17, "EP 条件范围应为 10^17（Salez）"
    assert SYSTEM_PRIME_BOUND == 100
    assert SYSTEM_K_BOUND == 10


# ============================================================
# 1. Layer 1：EP 实例验证
# ============================================================
def test_known_instances_have_valid_ones():
    valid = get_valid_known_instances()
    assert len(valid) >= 3, f"至少 3 个已知 EP 实例通过，实际 {valid}"
    # 至少包含 p=3,5,7（这三个 100% 确定）
    ps = {inst[0] for inst in valid}
    assert {3, 5, 7} <= ps, f"p=3,5,7 应都在 valid 里，实际 ps={ps}"


def test_each_known_instance():
    for (p, a, b, c) in get_valid_known_instances():
        assert verify_ep_instance(p, a, b, c), f"4/{p} = 1/{a}+1/{b}+1/{c} 不成立"


def test_invalid_instance_rejected():
    # 4/3 != 1/1 + 1/5 + 1/5
    assert not verify_ep_instance(3, 1, 5, 5)
    # 4/7 != 1/2 + 1/14 + 1/14
    assert not verify_ep_instance(7, 2, 14, 14)


# ============================================================
# 2. Layer 2：归约恒等式（P ⟹ Q 的实例验证）
# ============================================================
def test_reduction_identity_pure():
    """纯代数：不依赖 EP，给定 (p,a,b,c,k)，验证 4/(pk) = 1/(ak)+1/(bk)+1/(ck)。"""
    # 注意：verify_reduction_identity 只验证恒等式，不验证 EP 前提
    # 即使 EP 不成立，恒等式也可能成立（因为它是"若 P 则 Q"的 Q）
    # 所以这里不先 verify_ep_instance，直接验证 Q 的代数形式
    for (p, a, b, c) in get_valid_known_instances():
        for k in [1, 2, 3, 5, 10]:
            assert verify_reduction_identity(p, a, b, c, k), \
                f"p={p},k={k} 归约恒等式不成立"


def test_reduction_from_ep():
    """完整 P ⟹ Q：先 EP 实例，再归约。"""
    for (p, a, b, c) in get_valid_known_instances():
        for k in [1, 2, 3, 5, 10]:
            ok, reason = verify_reduction_from_ep(p, a, b, c, k)
            assert ok, reason


def test_reduction_from_ep_rejects_bad_ep():
    """EP 实例不成立时，verify_reduction_from_ep 返回 False。"""
    ok, reason = verify_reduction_from_ep(3, 1, 5, 5, 2)  # 4/3 != 1/1+1/5+1/5
    assert not ok
    assert "EP 实例不成立" in reason


def test_reduction_cartesian_product():
    """笛卡尔积：已知 EP 实例 × k ∈ [1, SYSTEM_K_BOUND]。"""
    valid = get_valid_known_instances()
    total = 0
    for (p, a, b, c) in valid:
        for k in range(1, SYSTEM_K_BOUND + 1):
            ok, reason = verify_reduction_from_ep(p, a, b, c, k)
            assert ok, reason
            total += 1
    assert total == len(valid) * SYSTEM_K_BOUND


# ============================================================
# 3. Layer 3：n ≡ 0 (mod 4) 特例
# ============================================================
def test_mod4_zero_small():
    for k in range(1, 101):
        assert verify_mod4_zero(k), f"k={k} 不成立"


def test_mod4_zero_10k():
    """k ≤ 10^4 全验证（< 1 秒）。"""
    for k in range(1, 10001):
        assert verify_mod4_zero(k), f"k={k} 不成立"


def test_mod4_zero_specific():
    """几个具体值。"""
    for k in [1, 2, 3, 4, 5, 10, 100, 1000]:
        assert verify_mod4_zero(k)


# ============================================================
# 4. 边界
# ============================================================
def test_zero_k_rejected():
    assert not verify_mod4_zero(0)
    assert not verify_reduction_identity(3, 1, 4, 12, 0)


def test_negative_rejected():
    assert not verify_mod4_zero(-1)
    assert not verify_reduction_identity(3, 1, 4, 12, -1)