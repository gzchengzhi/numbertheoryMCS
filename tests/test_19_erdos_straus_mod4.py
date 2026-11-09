# tests/test_19_erdos_straus_mod4.py
"""19.0.3 p ≡ 3 (mod 4) 的 Erdős–Straus 证明测试。

关键公式：4/p - 1/a = 1/m（m 正整数），不是 4/p - 4/a。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import sympy
import pytest

from tools.erdos_straus_mod4 import (
    generate_candidates,
    filter_candidates,
    try_candidate,
    find_optimal_candidate,
    verify_all_p3_mod4,
    solidify_candidate,
)


# ============================================================
# 1. 候选生成
# ============================================================
def test_generate_candidates_p3():
    cands = generate_candidates(3, n_candidates=5)
    assert 1 in cands  # (3+1)/4 = 1


def test_generate_candidates_p7():
    cands = generate_candidates(7, n_candidates=5)
    assert 2 in cands  # (7+1)/4 = 2


def test_generate_candidates_p1_mod4():
    assert generate_candidates(5) == []
    assert generate_candidates(13) == []


# ============================================================
# 2. 候选筛选
# ============================================================
def test_filter_p7():
    cands = generate_candidates(7, n_candidates=10)
    filtered = filter_candidates(7, cands)
    # (7+1)/4=2：4/7 - 1/2 = 8/14-7/14=1/14，m=14 ✓
    assert (2, 14) in filtered
    # (7-3)/4=1：4/7 - 1/1 = -3/7 < 0，排除
    assert all(a != 1 for (a, _) in filtered)


def test_filter_p11():
    cands = generate_candidates(11, n_candidates=10)
    filtered = filter_candidates(11, cands)
    # (11+1)/4=3：4/11 - 1/3 = 12/33-11/33=1/33，m=33 ✓
    assert (3, 33) in filtered


# ============================================================
# 3. 单候选验证
# ============================================================
def test_try_candidate_p3():
    ok, abc = try_candidate(3, 1)
    assert ok
    assert abc == (1, 4, 12)


def test_try_candidate_p7():
    ok, abc = try_candidate(7, 2)
    assert ok
    assert abc == (2, 15, 210)


def test_try_candidate_p11():
    ok, abc = try_candidate(11, 3)
    assert ok
    assert abc == (3, 34, 1122)


def test_try_candidate_bad():
    # a=1 对 p=7 不行（4/7 - 1/1 < 0）
    ok, abc = try_candidate(7, 1)
    assert not ok
    assert abc is None


# ============================================================
# 4. 最优候选
# ============================================================
def test_optimal_p3():
    assert find_optimal_candidate(3) == (1, 4, 12)


def test_optimal_p7():
    assert find_optimal_candidate(7) == (2, 15, 210)


def test_optimal_p1_mod4_none():
    assert find_optimal_candidate(5) is None
    assert find_optimal_candidate(13) is None


# ============================================================
# 5. 全范围验证
# ============================================================
def test_verify_all_p3_mod4_100():
    stats = verify_all_p3_mod4(100)
    assert stats["passed"] == stats["total"], f"failed: {stats['failed']}"
    assert stats["pass_rate"] == "100%"


def test_verify_all_p3_mod4_10k():
    stats = verify_all_p3_mod4(10000)
    assert stats["passed"] == stats["total"], f"failed: {stats['failed']}"


# ============================================================
# 6. 学习：solidify 写回神经元
# ============================================================
def test_solidify_candidate():
    from adaptive_store import AdaptiveStore
    store = AdaptiveStore()
    store.concept_neurons = {}
    store._neurons_built = True
    nid = solidify_candidate(store, 7, 2)
    assert nid is not None
    assert nid in store.concept_neurons
    neuron = store.concept_neurons[nid]
    assert neuron["head_pattern"][0] == "unit_fraction_sum"