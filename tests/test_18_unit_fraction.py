# tests/test_18_unit_fraction.py
"""18.0.3b 测试：1/n = 1/x + 1/y + 1/z 自主证明。"""
import json
import glob
import os
import pytest

from adaptive_store import AdaptiveStore
from deep_recursive_prover import DeepRecursiveProver


@pytest.fixture(scope="module")
def store():
    s = AdaptiveStore()
    for f in sorted(glob.glob("theorems/*.jsonl")):
        s.load_jsonl(f)
    if os.path.exists("theorems/concept_neurons.json"):
        with open("theorems/concept_neurons.json", encoding="utf-8") as fh:
            s.concept_neurons = json.load(fh)["concept_neurons"]
    if os.path.exists("theorems/18_0_unit_fraction.json"):
        with open("theorems/18_0_unit_fraction.json", encoding="utf-8") as fh:
            uf = json.load(fh)
        for nid, n in uf.get("concept_neurons", {}).items():
            s.concept_neurons.setdefault(nid, n)
    return s


def test_unit_fraction_sum_specific(store):
    """n=3 时，1/3 = 1/6 + 1/9 + 1/18。"""
    rp = DeepRecursiveProver(store, verbose=False)
    proof = rp.prove_deep(
        "unit_fraction_sum(times(2,3), times(3,3), times(6,3), 3)",
        premises=[],
        verbose=False)
    assert proof is not None


def test_unit_fraction_sum_general(store):
    """forall(n, 1/n = 1/(2n) + 1/(3n) + 1/(6n))。"""
    rp = DeepRecursiveProver(store, verbose=False)
    proof = rp.prove_deep(
        "unit_fraction_sum(times(2,n), times(3,n), times(6,n), n)",
        premises=["gt(n, 0)"],
        verbose=True)
    assert proof is not None


def test_unit_fraction_sum_symbolic_sympy(store):
    """sympy 验证 1/n = 1/(2n) + 1/(3n) + 1/(6n)。"""
    import sympy
    from sympy_bridge import to_sympy
    n = sympy.Symbol('n', positive=True, integer=True)
    expr = sympy.Eq(1/n, 1/(2*n) + 1/(3*n) + 1/(6*n))
    assert sympy.simplify(expr) == sympy.true