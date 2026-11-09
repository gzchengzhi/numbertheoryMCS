"""14.0.5e: 深度题测试的 fixture。只注册 fixture，不导出辅助函数。"""
import os, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

import numtheory_prover
numtheory_prover.ENABLE_SUBST_CONSISTENCY = True
numtheory_prover.ENABLE_EMPTY_LOWER = True

from tools.deep_recursive_prover import DeepRecursiveProver
from tests.deep._helpers import load_deep_cases, make_deep_store


@pytest.fixture
def deep_cases():
    return load_deep_cases()


@pytest.fixture
def deep_rp():
    s = make_deep_store(max_depth=8)
    return DeepRecursiveProver(
        s, iso_edges_path=os.path.join(ROOT, "data", "iso_edges.json"))