# tests/bench/test_wm_pr3.py
import json, glob, os, pytest
from adaptive_prover import AdaptiveProver
from adaptive_store import AdaptiveStore
from numtheory_prover import parse_goal
from working_memory import WorkingMemory
from probe import SearchProbe, SearchBudgetExceeded

CASES_SCHEMA = [
    ("divides_transitive",   "divides(a,c)",        ["divides(a,b)", "divides(b,c)"]),
    ("congruent_transitive", "congruent(a,c,m)",    ["congruent(a,b,m)", "congruent(b,c,m)"]),
    ("prime_implies_gt",     "gt(p,1)",             ["prime(p)"]),
    ("divisor_to_divides",   "divides(d,n)",        ["divisor(d,n)"]),
    ("congruent_to_divides", "divides(m,minus(a,b))", ["congruent(a,b,m)"]),
]

# CASES_CHAIN_FALLBACK = [
#     # 神经元只有 T::divides::@0-@1（传递），但这题需要“整除的加法封闭性”
#     ("divides_add_closure", "divides(a, plus(b,c))", ["divides(a,b)", "divides(a,c)"]),
#     # 神经元只有 T::congruent::@0-@1（传递），但这题需要“同余的乘法”
#     ("congruent_mul", "congruent(times(a,c), times(b,c), m)", ["congruent(a,b,m)"]),
#     # 神经元只有 S::gt<-prime，但这题需要“素数的平方大于1”
#     ("prime_square_gt", "gt(power(p,2), 1)", ["prime(p)"]),
#     # 神经元没有“gcd 结合律”，强制链式
#     ("gcd_assoc", "equals(gcd(gcd(a,b),c), gcd(a,gcd(b,c)))", []),
#     # 神经元没有“lcm 与 gcd 的关系”，强制链式
#     ("lcm_gcd_relation", "equals(times(lcm(a,b),gcd(a,b)), times(a,b))", []),
# ]

def _load_store():
    store = AdaptiveStore()
    if os.path.exists("theorems.jsonl"):
        store.load_jsonl("theorems.jsonl")
    for p in sorted(glob.glob("theorems/*.jsonl")):
        store.load_jsonl(p)
    store.load_weights()
    store.load_dependency_records()
    store.load_neurons("theorems/concept_neurons.json")
    return store

def _run(case_id, goal_str, premises, wm_on, tmp_path):
    goal_pred = parse_goal(goal_str)
    assert goal_pred is not None
    store = _load_store()
    probe = SearchProbe()
    from working_memory import NoopWorkingMemory
    wm = None if wm_on else NoopWorkingMemory()
    ap = AdaptiveProver(store, max_depth=12, max_nodes=50_000,
                        max_steps=10_000, working_memory=wm, probe=probe)
    probe.start("baseline")
    success, reason, result = False, "", None
    try:
        result = ap.prove(goal_str, premises=premises, verbose=False)
        success = result is not None
        reason = "ok" if success else "no_proof"
    except SearchBudgetExceeded as ex:
        reason = f"budget_exceeded: {ex}"
    except Exception as ex:
        reason = f"error: {ex!r}"
    finally:
        probe.finish(success, fell_back=not success, reason=reason)
    rec = {
        "case": case_id, "wm_on": wm_on,
        "nodes_visited": probe.nodes_visited, "probe_max_depth": probe.max_depth,
        "elapsed_ms": round(probe.elapsed_ms, 2),
        "success": success, "reason": reason,
        "result_preview": str(result)[:200],
    }
    (tmp_path / f"wm_{'on' if wm_on else 'off'}_{case_id}.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[{case_id} wm={'on' if wm_on else 'off'}] {rec}")
    return rec

@pytest.mark.parametrize("case_id,goal_str,premises", CASES_SCHEMA)
def test_wm_on_off_compare(case_id, goal_str, premises, tmp_path):
    off = _run(case_id, goal_str, premises, False, tmp_path)
    on  = _run(case_id, goal_str, premises, True,  tmp_path)
    # 验收：WM 开启不退化 success；nodes_visited 不超过 off
    assert on["success"] == off["success"], f"{case_id}: WM 改变了解题结果"
    assert on["nodes_visited"] <= off["nodes_visited"], \
        f"{case_id}: WM 增加了 {on['nodes_visited'] - off['nodes_visited']} 个节点"