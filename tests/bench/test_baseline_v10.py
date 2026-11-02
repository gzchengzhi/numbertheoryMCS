# tests/bench/test_baseline_v10.py
import json, glob, os, pytest
from adaptive_prover import AdaptiveProver
from adaptive_store import AdaptiveStore
from numtheory_prover import parse_goal
from probe import SearchProbe, SearchBudgetExceeded

# ★ 组1：定理库可覆盖的基础题（WM 剪枝的数值验收对象）
CASES_BASIC = [
    ("prime_3",        "prime(3)"),
    ("divides_2_4",    "divides(2,4)"),
    ("congruent_3_7_2","congruent(3,7,2)"),
    ("gt_5_3",         "gt(5,3)"),
    ("coprime_4_9",    "coprime(4,9)"),
]

# ★ 组2：超纲题（10.0/10.1 目标题，baseline 只记“缺什么”，不参与数值验收）
CASES_HARD = [
    ("two_digit_times9",
     "exists(n, and(ge(n,10), le(n,99), equals(digit_sum(times(9,n)), digit_sum(n))))"),
    ("wolstenholme_p2",
     "forall(p, implies(and(prime(p), gt(p,3)), divides(power(p,2), numerator(harmonic(minus(p,1))))))"),
    ("n_2000_primes_2n1",
     "exists(n, and(equals(omega(n),2000), divides(n, plus(power(2,n),1))))"),
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

def _run_case(case_id, goal_str, max_depth, tmp_path, group):
    goal_pred = parse_goal(goal_str)
    assert goal_pred is not None, f"parse_goal 失败: {goal_str}"

    store = _load_store()
    probe = SearchProbe()
    ap = AdaptiveProver(store, max_depth=max_depth,
                        max_nodes=50_000, max_steps=10_000, probe=probe)

    probe.start("baseline")
    success, reason, result = False, "", None
    try:
        result = ap.prove(goal_str, verbose=False)
        success = result is not None
        reason = "ok" if success else "no_proof"
    except SearchBudgetExceeded as ex:
        reason = f"budget_exceeded: {ex}"
    except Exception as ex:
        reason = f"error: {ex!r}"
    finally:
        probe.finish(success, fell_back=not success, reason=reason)

    record = {
        "case": case_id, "group": group, "max_depth_arg": max_depth,
        "max_steps_arg": 10_000, "max_nodes_arg": 50_000,
        "goal_pred": str(goal_pred),
        "strategy": probe.strategy, "fell_back": probe.fell_back,
        "nodes_visited": probe.nodes_visited, "probe_max_depth": probe.max_depth,
        "elapsed_ms": round(probe.elapsed_ms, 2),
        "success": success, "reason": reason,
        "result_preview": str(result)[:300],
    }
    (tmp_path / f"baseline_{group}_{case_id}_d{max_depth}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[{group}/{case_id} d={max_depth}] {record}")

@pytest.mark.parametrize("case_id,goal_str", CASES_BASIC)
@pytest.mark.parametrize("max_depth", [12])
def test_baseline_basic(case_id, goal_str, max_depth, tmp_path):
    _run_case(case_id, goal_str, max_depth, tmp_path, "basic")

@pytest.mark.parametrize("case_id,goal_str", CASES_HARD)
@pytest.mark.parametrize("max_depth", [12, 8, 6])
def test_baseline_hard(case_id, goal_str, max_depth, tmp_path):
    _run_case(case_id, goal_str, max_depth, tmp_path, "hard")