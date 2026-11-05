# tools/diagnose.py
"""17.0.3 新题自诊断 + 自动学。

用法：
  python -m tools.diagnose --goal "divides(b, a)" --premise "equals(a, plus(times(b,q), 0))"
  python -m tools.diagnose --goal "..." --premise "..." --auto-learn
"""
import argparse
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# 辅助：pattern → Pred
# ============================================================
def _pattern_to_pred(pat, store):
    """[name, [args...]] → Pred。"""
    from numtheory_prover import Pred, Var, Const, parse_term
    if not isinstance(pat, (list, tuple)) or len(pat) < 2:
        return None
    name = pat[0]
    if not isinstance(name, str):
        return None
    args = []
    for a in pat[1]:
        if not isinstance(a, str):
            return None
        if a.lstrip("-").isdigit():
            args.append(Const(a))
        elif len(a) == 1 and a.isalpha():
            args.append(Var(a))
        else:
            args.append(parse_term(a))
    return Pred(name, tuple(args))


def _is_comparison_only(body):
    """body 全是 gt/ge/lt/le → 比较谓词推不出代数等式，拒。"""
    comparisons = {"gt", "ge", "lt", "le"}
    if not body:
        return False
    return all(b.name in comparisons for b in body)


# ============================================================
# 主诊断
# ============================================================

HIGH_ORDER_PREDS = {"forall", "exists", "not_exists", "implies", "and", "or", "not"}

def diagnose(goal_str: str, premises: list, verbose: bool = False,
             make_rp_fn=None, auto_learn: bool = False) -> int:
    """诊断 + 可选自动学。返回 0 成功，1 失败。"""
    if make_rp_fn is None:
        from tools.bench_competition import make_rp as make_rp_fn
    from tools.learn_from_failure import suggest_candidates
    from numtheory_prover import HornClause

    rp = make_rp_fn()
    print(f"[diagnose] goal: {goal_str}")
    print(f"[diagnose] premises: {len(premises)} 条")
    print(f"[diagnose] 尝试证明...")

    proof = rp.prove(goal_str, premises=premises, verbose=False)
    if proof is not None:
        print(f"[diagnose] ✅ 成功，{len(proof)} 步")
        for s in proof:
            print(f"  - {s.clause.id} {s.strategy}")
        return 0

    print(f"[diagnose] ❌ 失败")
    head_pred = goal_str.split("(", 1)[0].strip()
    if head_pred in HIGH_ORDER_PREDS:
        print(f"[diagnose] 高阶谓词 {head_pred}，13.x 不直接支持")
        print(f"[diagnose] 提示：需手工转换（如 forall → exists，exists(xy) → exists(x, exists(y))）")
        return 1
    cands = suggest_candidates(goal_str, premises, rp.store)
    if not cands:
        print(f"[diagnose] 无候选（premises 为空或已覆盖）")
        return 1

    print(f"[diagnose] 候选神经元（{len(cands)} 条）：")
    for c in cands:
        print(f"  - {c['neuron_id']}")
        print(f"    head: {c['head_pattern']}")
        print(f"    lower: {c['lower']}")

    if not auto_learn:
        print(f"[diagnose] 提示：加 --auto-learn 自动合入")
        return 1

    # 17.0.3：自动验证 + 合入
    from tools.verify_neuron import verify_by_structure

    added = 0
    for c in cands[:3]:
        nid = c["neuron_id"]
        if nid in rp.store.concept_neurons:
            continue
        head = _pattern_to_pred(c["head_pattern"], rp.store)
        body = [_pattern_to_pred(lo, rp.store) for lo in c["lower"]]
        if head is None or any(b is None for b in body):
            print(f"  ✗ {nid}: 模式解析失败")
            continue
        if _is_comparison_only(body):
            print(f"  ✗ {nid}: body 全是比较谓词，拒绝")
            continue
        clause = HornClause(
            id=f"VERIFY_{nid}", name="auto-learn verify",
            head=head, body=body)
        if verify_by_structure(clause) is not True:
            print(f"  ✗ {nid}: structure 验证失败")
            continue
        triangle = {
            "neuron": nid, "type": "single", "lower": c["lower"],
            "mediator": None, "anchor": None,
            "head_pattern": c["head_pattern"], "N": 1, "weight": 1.0,
        }
        rp.store.add_triangle(triangle, "AUTO_LEARN")
        added += 1
        print(f"  ✅ 合入 {nid}")

    if added == 0:
        print(f"[diagnose] 无候选通过验证")
        return 1

    print(f"[diagnose] 合入 {added} 条，重试...")
    proof = rp.prove(goal_str, premises=premises, verbose=False)
    if proof is not None:
        print(f"[diagnose] ✅ 重试成功，{len(proof)} 步")
        return 0
    print(f"[diagnose] ❌ 重试失败")

    
    return 1


# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--goal", required=True)
    ap.add_argument("--premise", action="append", default=[])
    ap.add_argument("--auto-learn", action="store_true",
                    help="失败时自动验证并合入候选神经元")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    sys.exit(diagnose(args.goal, args.premise, args.verbose,
                      auto_learn=args.auto_learn))