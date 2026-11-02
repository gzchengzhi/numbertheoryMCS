# tests/bench/test_wm_chain_fallback.py
import json, glob, os, pytest
from adaptive_prover import AdaptiveProver
from adaptive_store import AdaptiveStore
from numtheory_prover import parse_goal
from working_memory import NoopWorkingMemory
from probe import SearchProbe, SearchBudgetExceeded

CASES_CHAIN_FALLBACK = [
    # divides 的减法封闭：定理库有 M1-013（divides(a,b) ∧ divides(a,c) → divides(a, b-c)），但神经元库没有这个图式
    ("divides_sub", "divides(a, minus(b,c))", ["divides(a,b)", "divides(a,c)"]),
    # divides 的线性组合：定理库有 M1-015（divides(a,b) ∧ divides(a,c) → divides(a, m*b+n*c)），神经元库没有
    ("divides_linear", "divides(a, plus(times(m,b), times(n,c)))", ["divides(a,b)", "divides(a,c)"]),
    # congruent 的加法：定理库有 M4-014（congruent(a,b,m) ∧ congruent(c,d,m) → congruent(a+c,b+d,m)），神经元库没有
    ("congruent_add", "congruent(plus(a,c), plus(b,d), m)", ["congruent(a,b,m)", "congruent(c,d,m)"]),

]

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

def _warmup():
    from adaptive_prover import AdaptiveProver
    from adaptive_store import AdaptiveStore
    store = AdaptiveStore()
    store.load_neurons("theorems/concept_neurons.json")
    ap = AdaptiveProver(store)
    ap.prove("prime(3)", verbose=False)

def _run(case_id, goal_str, premises, wm_on, tmp_path):
    goal_pred = parse_goal(goal_str)
    assert goal_pred is not None, f"parse_goal 失败: {goal_str}"
    store = _load_store()
    probe = SearchProbe()
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
    (tmp_path / f"chain_{'on' if wm_on else 'off'}_{case_id}.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[{case_id} wm={'on' if wm_on else 'off'}] {rec}")
    return rec

@pytest.mark.timeout(30)   # 每题 30s 硬超时，超时记 timeout
@pytest.mark.parametrize("case_id,goal_str,premises", CASES_CHAIN_FALLBACK)
def test_wm_chain_fallback(case_id, goal_str, premises, tmp_path):
    _warmup()
    off = _run(case_id, goal_str, premises, False, tmp_path)
    on  = _run(case_id, goal_str, premises, True,  tmp_path)
    assert on["success"] == off["success"], f"{case_id}: WM 改变了解题结果"
    print(f"  [diff] nodes: {on['nodes_visited'] - off['nodes_visited']}, "
          f"ms: {on['elapsed_ms'] - off['elapsed_ms']:.2f}")