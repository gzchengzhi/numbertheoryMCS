# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 19:08:59 2026

@author: gzche
"""

# tests/domains/test_13_dirichlet.py
"""13.0.3 的目标：C098~C102。13.0.1 时 0/5，13.0.3 后 5/5。"""
import sys, os, json
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from adaptive_store import AdaptiveStore
from recursive_prover import RecursiveProver
from concept_domain import DomainRegistry

import numtheory_prover
numtheory_prover.ENABLE_SUBST_CONSISTENCY = True


@pytest.fixture(scope="module")
def domain_rp():
    import glob
    store = AdaptiveStore()
    for f in sorted(glob.glob("theorems/*.jsonl")):
        base = os.path.basename(f)
        if "learn_log" in base or "candidates" in base:
            continue
        store.load_jsonl(f)
    with open("theorems/concept_neurons.json", encoding="utf-8") as fh:
        data = json.load(fh)
    store.concept_neurons = data["concept_neurons"]
    store._neurons_built = True
    if hasattr(store, "_head_index"):
        del store._head_index
    if hasattr(store, "_clause_head_index"):
        del store._clause_head_index
    reg = DomainRegistry("domains")
    reg.load_all_into(store)
    return RecursiveProver(store, iso_edges_path="data/iso_edges.json")


def load_cases():
    path = "domains/dirichlet/cases.jsonl"
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


ALL = load_cases()
XFAIL = {c["id"] for c in ALL}   # 13.0.1 时全部 xfail


@pytest.mark.parametrize("case_id", [c["id"] for c in ALL])
# @pytest.mark.xfail(reason="13.0.3 目标", strict=False)
def test_dirichlet(domain_rp, case_id):
    case = next(c for c in ALL if c["id"] == case_id)
    proof = domain_rp.prove(case["goal"], premises=case.get("premises", []),
                            verbose=False)
    assert proof is not None
    assert any(s.strategy.startswith("neuron:") for s in proof)