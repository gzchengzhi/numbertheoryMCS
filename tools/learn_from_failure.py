# tools/learn_from_failure.py
"""16.0.2 B：失败驱动神经元生成（交互式）。

流程：
  1. 跑 bench，收集 fallback 题
  2. 从 fallback 生成神经元候选
  3. 逐条显示候选 + 建议，Y/N 确认
  4. Y 自动合入 theorems/16_0_learned_neurons.json（合并不覆盖）
"""
import json
import os
from typing import Dict, List


LEARNED_PATH = "data/16_0_learned_neurons.json"


# ============================================================
# 1. 收集 fallback
# ============================================================
def collect_fallbacks(verbose: bool = False) -> List[Dict]:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tools.bench_competition import make_rp, load_cases
    cases = load_cases()
    fallbacks = []
    for case in cases:
        rp = make_rp()
        proof = rp.prove(case["goal"], premises=case.get("premises", []),
                         verbose=False)
        if proof is None:
            continue
        strategies = [s.strategy for s in proof]
        if any(s.startswith("neuron:") or s.startswith("iso:") for s in strategies):
            continue
        used = [s.clause.id for s in proof]
        fallbacks.append({
            "id": case["id"],
            "goal": case["goal"],
            "premises": case.get("premises", []),
            "used_clauses": used,
            "strategies": strategies,
        })
        if verbose:
            print(f"[fallback] {case['id']}: {case['goal']} <- {used}")
    return fallbacks


# ============================================================
# 2. 生成候选
# ============================================================
def _parse_pattern(s: str):
    """字符串谓词 → [name, [args...]]，正确处理嵌套括号。

    "divides(b, a)" → ["divides", ["b", "a"]]
    "equals(a, plus(times(b,q), 0))" → ["equals", ["a", "plus(times(b,q), 0)"]]
    """
    s = s.strip()
    if "(" not in s:
        return [s, []]
    name, rest = s.split("(", 1)
    # rest 末尾一定有且仅有一个 ")"，去掉最外层
    rest = rest.strip()
    if rest.endswith(")"):
        rest = rest[:-1]
    args, depth, cur = [], 0, ""
    for ch in rest:
        if ch == "," and depth == 0:
            args.append(cur.strip())
            cur = ""
        else:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            cur += ch
    if cur.strip():
        args.append(cur.strip())
    return [name.strip(), args]

def suggest_candidates(goal_str: str, premises: List[str],
                       store) -> List[Dict]:
    """16.0.3a：从单条失败题生成候选，不写入文件。

    返回 [] 表示：
      - premises 为空
      - used_clauses 全是计算型（这里 used_clauses 固定为 AUTO，跳过）
      - store 里已有相同 head_pattern + lower 的神经元（去重）
    """
    premises = premises or []
    if not premises:
        return []

    goal_pattern = _parse_pattern(goal_str)
    lower_patterns = [_parse_pattern(p) for p in premises]

    # 去重：store 里已有相同 head_pattern + lower 的跳过
    for existing_id, existing in store.concept_neurons.items():
        if (existing.get("head_pattern") == goal_pattern
                and existing.get("lower") == lower_patterns):
            return []

    goal_pred = goal_str.split("(", 1)[0].strip()
    body_preds = [p.split("(", 1)[0].strip() for p in premises]
    nid = (f"NEURON::S::{goal_pred}<-{'+'.join(sorted(body_preds))}"
           f"::arity=auto")
    return [{
        "neuron_id": nid,
        "head_pattern": goal_pattern,
        "lower": lower_patterns,
        "source": "AUTO",
        "used_clauses": ["AUTO"],
    }]

def _is_valid_candidate(fb: Dict) -> bool:
    """候选有效性规则。

    1. 跳过 used_clauses 全是 NEURON_TO_THM（15.0.2 verified 已覆盖）
    2. 跳过 used_clauses 含 SYMPY/COMPUTED/SYM_INEQ（计算型）
    3. premises 为空，跳过
    """
    used = fb["used_clauses"]
    if all(u.startswith("NEURON_TO_THM") for u in used):
        return False
    if any(u in ("SYMPY", "COMPUTED", "SYM_INEQ") for u in used):
        return False
    if not fb["premises"]:
        return False
    return True


def generate_candidates(fallbacks, out_path="data/16_0_candidates.jsonl"):
    candidates = []
    for fb in fallbacks:
        if not _is_valid_candidate(fb):
            continue
        goal_pred = fb["goal"].split("(", 1)[0].strip()
        body_preds = [p.split("(", 1)[0].strip() for p in fb["premises"]]
        nid = (f"NEURON::S::{goal_pred}<-{'+'.join(sorted(body_preds))}"
               f"::arity=auto")
        candidates.append({
            "neuron_id": nid,
            "head_pattern": _parse_pattern(fb["goal"]),
            "lower": [_parse_pattern(p) for p in fb["premises"]],
            "source": fb["id"],
            "used_clauses": fb["used_clauses"],
        })
    return candidates


# ============================================================
# 3. 交互式审阅 + 自动合入
# ============================================================
def _load_learned(path: str = LEARNED_PATH) -> Dict:
    if not os.path.exists(path):
        return {"concept_neurons": {}, "neuron_edges": {}}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"concept_neurons": {}, "neuron_edges": {}}


def _save_learned(data: Dict, path: str = LEARNED_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _show_candidate(c: Dict, idx: int, total: int):
    print(f"\n[{idx}/{total}] {c['source']}")
    print(f"  neuron_id: {c['neuron_id']}")
    print(f"  head:  {c['head_pattern'][0]}({', '.join(c['head_pattern'][1])})")
    print(f"  lower: {len(c['lower'])} 条")
    for lo in c["lower"]:
        print(f"    - {lo[0]}({', '.join(lo[1])})")
    print(f"  used:  {c['used_clauses']}")
    # 建议
    if all(u.startswith("T") or u.startswith("INT-") for u in c["used_clauses"]):
        print(f"  建议: Y（13.x 定理 {c['used_clauses']} 证明，语义可信）")
    else:
        print(f"  建议: N（used_clauses 含非常规来源，需人工审阅）")


def review_and_merge(candidates: List[Dict]) -> int:
    """逐条 Y/N，Y 合入 16_0_learned_neurons.json。返回合入数。"""
    if not candidates:
        print("[learn] 无候选")
        return 0
    learned = _load_learned()
    existing = learned.get("concept_neurons", {})
    added = 0
    for idx, c in enumerate(candidates, 1):
        nid = c["neuron_id"]
        if nid in existing:
            print(f"\n[{idx}/{len(candidates)}] {c['source']}: 已存在，跳过")
            continue
        _show_candidate(c, idx, len(candidates))
        try:
            ans = input("  添加？[Y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n[learn] 中断")
            break
        if ans not in ("", "y", "yes"):
            print("  跳过")
            continue
        existing[nid] = {
            "neuron_id": nid,
            "type": "single",
            "lower": c["lower"],
            "mediator": None,
            "anchor": None,
            "head_pattern": c["head_pattern"],
            "N": 1,
            "weight": 1.0,
            "instances": [],
            "source": c["source"],
        }
        added += 1
        print(f"  ✅ 已加入 {nid}")
    learned["concept_neurons"] = existing
    _save_learned(learned)
    print(f"\n[learn] 合入 {added} 条，写入 {LEARNED_PATH}")
    return added

# def suggest_candidates(goal_str: str, premises: List[str],
#                        store) -> List[Dict]:
#     """16.0.3a：从单条失败题生成候选，不写入文件。"""
#     fb = {
#         "id": "AUTO",
#         "goal": goal_str,
#         "premises": premises or [],
#         "used_clauses": ["AUTO"],
#         "strategies": ["auto"],
#     }
#     if not _is_valid_candidate(fb):
#         return []
#     goal_pred = goal_str.split("(", 1)[0].strip()
#     body_preds = [p.split("(", 1)[0].strip() for p in fb["premises"]]
#     if not body_preds:
#         return []
#     nid = f"NEURON::S::{goal_pred}<-{'+'.join(sorted(body_preds))}::arity=auto"
#     # 去重：store 里已有同 head_pattern + lower 的跳过
#     for existing_id, existing in store.concept_neurons.items():
#         if (existing.get("head_pattern") == _parse_pattern(goal_str)
#                 and existing.get("lower") == [_parse_pattern(p) for p in fb["premises"]]):
#             return []
#     return [{
#         "neuron_id": nid,
#         "head_pattern": _parse_pattern(goal_str),
#         "lower": [_parse_pattern(p) for p in fb["premises"]],
#         "source": "AUTO",
#         "used_clauses": fb["used_clauses"],
#     }]

# ============================================================
# 入口
# ============================================================
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--auto-y", action="store_true",
                    help="全部自动 Y（跳过交互，用于 CI）")
    args = ap.parse_args()

    fbs = collect_fallbacks(verbose=args.verbose)
    print(f"\n[fallback] 共 {len(fbs)} 条")
    candidates = generate_candidates(fbs)
    print(f"[learn] 生成 {len(candidates)} 条候选")

    if args.auto_y:
        for c in candidates:
            print(f"\n{ c['source']}: {c['neuron_id']} → 自动 Y")
        # 全部合入
        learned = _load_learned()
        existing = learned.get("concept_neurons", {})
        added = 0
        for c in candidates:
            nid = c["neuron_id"]
            if nid in existing:
                continue
            existing[nid] = {
                "neuron_id": nid, "type": "single", "lower": c["lower"],
                "mediator": None, "anchor": None,
                "head_pattern": c["head_pattern"], "N": 1, "weight": 1.0,
                "instances": [], "source": c["source"],
            }
            added += 1
        learned["concept_neurons"] = existing
        _save_learned(learned)
        print(f"[learn] 合入 {added} 条，写入 {LEARNED_PATH}")
    else:
        review_and_merge(candidates)