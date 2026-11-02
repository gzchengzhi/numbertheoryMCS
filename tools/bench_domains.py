# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 19:04:49 2026

@author: gzche
"""

# tools/bench_domains.py
"""13.0 域批量测试：加载所有域，跑域内 cases，报告 pass/fail。"""
import sys, os, json, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

# 静音 DEBUG
import builtins
if not hasattr(builtins, "_nm_orig_print"):
    builtins._nm_orig_print = builtins.print
def _quiet(*a, **kw):
    if a and isinstance(a[0], str) and a[0].startswith(("[DEBUG", "[recursive]", "[neuron]", "[dbg]", "[trace]", "[concept]", "[fast]", "[sympy]")):
        return
    builtins._nm_orig_print(*a, **kw)
builtins.print = _quiet

from adaptive_store import AdaptiveStore
from recursive_prover import RecursiveProver
from concept_domain import DomainRegistry

import numtheory_prover
numtheory_prover.ENABLE_SUBST_CONSISTENCY = True


def make_rp():
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

    # ★ 加载所有域
    reg = DomainRegistry("domains")
    added = reg.load_all_into(store)
    return store, reg, added, RecursiveProver(
        store, iso_edges_path="data/iso_edges.json", verbose=False)


def main():
    
    store, reg, added, rp = make_rp()
    _nm_orig_print(f"\n[domains] 主库神经元: {len(store.concept_neurons) - sum(added.values())}")
    for name, n in added.items():
        _nm_orig_print(f"[domains]   {name}: +{n} 神经元")

    for name in reg.list_domains():
        d = reg.domains.get(name) or reg.register(name)
        cases = d.load_cases()
        if not cases:
            _nm_orig_print(f"\n[{name}] 无测试用例")
            continue
        _nm_orig_print(f"\n{'='*60}")
        _nm_orig_print(f"[{name}] {len(cases)} 题")
        _nm_orig_print(f"{'='*60}")
        pass_n = 0
        for case in cases:
            try:
                proof = rp.prove(case["goal"], premises=case.get("premises", []),
                                 verbose=False)
            except Exception as e:
                _nm_orig_print(f"  💥 {case['id']}  EXC: {e!r}")
                continue
            if proof is None:
                _nm_orig_print(f"  ❌ {case['id']}  FAIL")
            else:
                strategies = [s.strategy for s in proof]
                if any(s.startswith("neuron:") for s in strategies):
                    pass_n += 1
                    _nm_orig_print(f"  ✅ {case['id']}  NEURON  {strategies[0]}")
                else:
                    _nm_orig_print(f"  ⚠️ {case['id']}  FALLBACK  {strategies[:2]}")
        _nm_orig_print(f"\n  [{name}] {pass_n}/{len(cases)} pass")


if __name__ == "__main__":
    main()