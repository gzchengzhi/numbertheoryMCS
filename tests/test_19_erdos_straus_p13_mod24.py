# tests/test_19_erdos_straus_p13_mod24.py
"""19.0.5 p ≡ 13 (mod 24) 的 Erdős–Straus 三项分解测试。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import sympy
import pytest

from tools.erdos_straus_p13_mod24 import (
    construction_p13_mod24,
    verify_p13_mod24,
    verify_all_p13_mod24,
)


def test_construction_p13():
    assert construction_p13_mod24(13) == (4, 130, 20)


def test_construction_p37():
    assert construction_p13_mod24(37) == (10, 2405, 130)


def test_construction_p61():
    assert construction_p13_mod24(61) == (16, 10248, 336)


def test_construction_p109():
    # 程序实际输出：(28, 56462, 1036)
    assert construction_p13_mod24(109) == (28, 56462, 1036)


def test_construction_not_p13_mod24():
    assert construction_p13_mod24(5) is None
    assert construction_p13_mod24(17) is None
    assert construction_p13_mod24(73) is None


def test_construction_nonprime():
    assert construction_p13_mod24(34) is None
    assert construction_p13_mod24(85) is None


def test_verify_p13():
    ok, reason = verify_p13_mod24(13)
    assert ok, reason


def test_verify_p37():
    ok, reason = verify_p13_mod24(37)
    assert ok, reason


def test_verify_p61():
    ok, reason = verify_p13_mod24(61)
    assert ok, reason


def test_verify_p109():
    ok, reason = verify_p13_mod24(109)
    assert ok, reason


def test_verify_not_p13_mod24():
    ok, reason = verify_p13_mod24(17)
    assert not ok


def test_verify_all_p13_mod24_100():
    stats = verify_all_p13_mod24(100)
    assert stats["failed"] == [], f"failed: {stats['failed']}"
    assert stats["passed"] == stats["total"]


def test_verify_all_p13_mod24_10k():
    stats = verify_all_p13_mod24(10000)
    assert stats["failed"] == [], f"failed: {stats['failed']}"