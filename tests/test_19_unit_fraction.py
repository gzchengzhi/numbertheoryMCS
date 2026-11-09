# tests/test_19_unit_fraction.py
"""19.0.1 单位分数证明测试（选项 A：外围 sympy 验证）。

覆盖：
  - 枚举 (2,3,6)
  - sympy 符号/具体验证
  - 端到端：prove_deep 图式层命中 + verify_unit_fraction
  - solidify 写回后 head_pattern 带 times(2,n)，下次命中 subst 有构造值
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import sympy
import pytest

from tools.unit_fraction import (
    find_egyptian_3_terms,
    scale_equation,
    extract_n,
    verify_unit_fraction,
    solidify_unit_fraction,
)


# ---------- 独立 store，不依赖 bench_competition 的 monkey-patch ----------
def make_minimal_store():
    """只放 unit_fraction_sum + egyptian_3_terms 两个神经元，最小可复现。"""
    from adaptive_store import AdaptiveStore
    store = AdaptiveStore()
    store.concept_neurons = {
        "NEURON::S::unit_fraction_sum<-gt::arity=1": {
            "neuron_id": "NEURON::S::unit_fraction_sum<-gt::arity=1",
            "type": "single",
            "lower": [["gt", ["n", "0"]]],
            "mediator": None,
            "anchor": None,
            "head_pattern": ["unit_fraction_sum", ["x", "y", "z", "n"]],
            "N": 1, "weight": 1.0, "instances": [],
        },
        "NEURON::S::egyptian_3_terms::arity=3": {
            "neuron_id": "NEURON::S::egyptian_3_terms::arity=3",
            "type": "single",
            "lower": [],
            "mediator": None,
            "anchor": None,
            "head_pattern": ["egyptian_3_terms", ["2", "3", "6"]],
            "N": 1, "weight": 1.0, "instances": [],
        },
    }
    store._neurons_built = True
    return store


def make_rp(store=None):
    from deep_recursive_prover import DeepRecursiveProver
    if store is None:
        store = make_minimal_store()
    return DeepRecursiveProver(store)


# ============================================================
# 1. 枚举
# ============================================================
def test_find_egyptian():
    assert find_egyptian_3_terms() == (2, 3, 6)


def test_find_egyptian_identity():
    a, b, c = find_egyptian_3_terms()
    assert sympy.Rational(1, a) + sympy.Rational(1, b) + sympy.Rational(1, c) == 1


# ============================================================
# 2. scale_equation
# ============================================================
def test_scale_symbolic():
    n = sympy.Symbol("n", integer=True, positive=True)
    assert sympy.simplify(scale_equation(n, 2, 3, 6)) == 0


def test_scale_concrete():
    for k in [1, 2, 5, 100]:
        assert scale_equation(k, 2, 3, 6) == 0, f"n={k}"


# ============================================================
# 3. extract_n
# ============================================================
def test_extract_n_concrete():
    assert extract_n("unit_fraction_sum(x,y,z,5)") == 5
    assert extract_n("unit_fraction_sum(x,y,z,100)") == 100


def test_extract_n_symbolic():
    n = extract_n("unit_fraction_sum(x,y,z,n)")
    assert isinstance(n, sympy.Symbol)
    assert n.name == "n"


def test_extract_n_invalid():
    assert extract_n("divides(a,b)") is None
    assert extract_n("unit_fraction_sum(x,y,z)") is None


# ============================================================
# 4. verify_unit_fraction（不依赖 proof）
# ============================================================
def test_verify_symbolic_no_proof():
    ok, reason = verify_unit_fraction("unit_fraction_sum(x,y,z,n)", proof=None)
    assert ok, reason


def test_verify_concrete_no_proof():
    for k in [1, 2, 3, 5, 100, 999]:
        ok, reason = verify_unit_fraction(f"unit_fraction_sum(x,y,z,{k})", proof=None)
        assert ok, f"n={k}: {reason}"


# ============================================================
# 5. 端到端：prove_deep 图式层命中 + 外围验证
# ============================================================
def test_prove_deep_symbolic_hit():
    rp = make_rp()
    goal = "unit_fraction_sum(x,y,z,n)"
    proof = rp.prove_deep(goal, premises=["gt(n,0)"], verbose=False)
    assert proof is not None, "prove_deep 未命中（检查 lower=gt(n,0) 是否匹配）"
    assert proof.strategy.startswith("neuron:"), f"strategy={proof.strategy}"
    ok, reason = verify_unit_fraction(goal, proof)
    assert ok, reason


def test_prove_deep_concrete_hit():
    rp = make_rp()
    for k in [1, 2, 3]:
        goal = f"unit_fraction_sum(x,y,z,{k})"
        proof = rp.prove_deep(goal, premises=[f"gt({k},0)"], verbose=False)
        assert proof is not None, f"n={k} 未命中"
        assert proof.strategy.startswith("neuron:"), f"n={k} strategy={proof.strategy}"
        ok, reason = verify_unit_fraction(goal, proof)
        assert ok, f"n={k}: {reason}"


# ============================================================
# 6. solidify 写回后，head_pattern 带 times(2,n)，下次命中有构造值
# ============================================================
def test_solidify_then_hit_with_construct():
    store = make_minimal_store()
    rp = make_rp(store)
    goal = "unit_fraction_sum(x,y,z,n)"
    proof1 = rp.prove_deep(goal, premises=["gt(n,0)"], verbose=False)
    assert proof1 is not None
    ok, _ = verify_unit_fraction(goal, proof1)
    assert ok

    # solidify：写回 head_pattern 带 times(2,n)
    nid = solidify_unit_fraction(store)
    assert nid is not None
    assert nid in store.concept_neurons
    new_hp = store.concept_neurons[nid]["head_pattern"]
    assert new_hp[1][0] == "times(2,n)", f"head_pattern={new_hp}"

    # 第二次：重建 rp，图式层命中，subst 应有构造值
    rp2 = make_rp(store)
    proof2 = rp2.prove_deep(goal, premises=["gt(n,0)"], verbose=False)
    assert proof2 is not None, "solidify 后应能命中"
    subst_str = {str(k): str(v) for k, v in proof2.substitution.items()}
    assert subst_str.get("x") == "times(2,n)", f"subst={subst_str}"
    assert subst_str.get("y") == "times(3,n)", f"subst={subst_str}"
    assert subst_str.get("z") == "times(6,n)", f"subst={subst_str}"
    ok2, reason2 = verify_unit_fraction(goal, proof2)
    assert ok2, reason2