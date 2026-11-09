# tests/test_19_erdos_straus_p1_3overp.py
"""19.0.4 p ≡ 5 (mod 12) 的 1/p + 3/p 路径测试。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import sympy
import pytest

from tools.erdos_straus_p1_3overp import (
    construction_p5_mod12,
    verify_p5_mod12,
    verify_all_p5_mod12,
)


# ============================================================
# 1. 构造
# ============================================================
def test_construction_p5():
    r = construction_p5_mod12(5)
    assert r == (5, 2, 10)


def test_construction_p17():
    r = construction_p5_mod12(17)
    assert r == (17, 6, 102)


def test_construction_p29():
    r = construction_p5_mod12(29)
    assert r == (29, 10, 290)


def test_construction_not_p5_mod12():
    # p=13 (13 ≡ 1 mod 12)，返回 None
    assert construction_p5_mod12(13) is None
    # p=7 (7 ≡ 7 mod 12)
    assert construction_p5_mod12(7) is None
    # p=5 非素数？5 是素数，OK。试 p=1
    assert construction_p5_mod12(1) is None


# ============================================================
# 2. 验证
# ============================================================
def test_verify_p5():
    ok, reason = verify_p5_mod12(5)
    assert ok, reason


def test_verify_p17():
    ok, reason = verify_p5_mod12(17)
    assert ok, reason


def test_verify_p29():
    ok, reason = verify_p5_mod12(29)
    assert ok, reason


def test_verify_not_p5_mod12():
    ok, reason = verify_p5_mod12(13)
    assert not ok


# ============================================================
# 3. 全范围验证
# ============================================================
def test_verify_all_p5_mod12_100():
    stats = verify_all_p5_mod12(100)
    assert stats["failed"] == [], f"failed: {stats['failed']}"
    assert stats["passed"] == stats["total"]


def test_verify_all_p5_mod12_10k():
    stats = verify_all_p5_mod12(10000)
    assert stats["failed"] == [], f"failed: {stats['failed']}"