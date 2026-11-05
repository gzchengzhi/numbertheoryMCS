# tools/expand_bench.py
"""15.0.5 扩题：12_0_competition.jsonl + 定理库 → cases.jsonl，去重后补到 target。

用法：
  python -m tools.expand_bench --dry-run -v
  python -m tools.expand_bench --target 200 --only-simple
  python -m tools.expand_bench --target 200          # 含高阶谓词

纪律：
  - 不修改 13.x 定理库
  - 只追加 cases.jsonl，不覆盖
  - 去重：goal + 排序后 premises 归一化签名
  - --only-simple：只保留 13.x 已支持的谓词（pass 率稳 ≥95%）
"""
import json
import os
import sys
from typing import Dict, List, Set

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# 13.x 已支持的谓词（sympy_decls + 神经元库实测）
SIMPLE_PREDS = {
    "divides", "congruent", "equals", "prime", "coprime",
    "gt", "ge", "lt", "le", "odd", "even",
    "quadratic_residue", "nonzero", "sum_to_n",
}


def _norm(goal: str, premises: List[str]) -> str:
    return goal + "|" + "|".join(sorted(premises or []))


def _pred_of(s: str) -> str:
    return s.split("(", 1)[0].strip()


def _is_simple(rec: Dict) -> bool:
    """head 和 body 的谓词都在 SIMPLE_PREDS 里。"""
    head_pred = _pred_of(rec["head"])
    if head_pred not in SIMPLE_PREDS:
        return False
    for b in rec.get("body", []):
        if _pred_of(b) not in SIMPLE_PREDS:
            return False
    return True


def load_jsonl(path: str) -> List[Dict]:
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def expand(target: int = 200, only_simple: bool = False,
           dry_run: bool = False, verbose: bool = False) -> int:
    cases_path = os.path.join(
        ROOT, "tests", "bench", "competition", "cases.jsonl")
    comp_path = os.path.join(ROOT, "theorems", "12_0_competition.jsonl")

    cases = load_jsonl(cases_path)
    comp = load_jsonl(comp_path)

    seen: Set[str] = set()
    for c in cases:
        seen.add(_norm(c["goal"], c.get("premises", [])))

    added: List[Dict] = []
    next_n = len(cases) + 1
    for rec in comp:
        if len(cases) + len(added) >= target:
            break
        if not rec.get("head"):
            continue
        if only_simple and not _is_simple(rec):
            if verbose:
                print(f"  跳过 {rec['id']}（高阶谓词）")
            continue
        goal = rec["head"]
        premises = rec.get("body", [])
        sig = _norm(goal, premises)
        if sig in seen:
            continue
        seen.add(sig)
        new_id = f"X{next_n:03d}"
        next_n += 1
        added.append({
            "id": new_id,
            "statement": rec.get("name", rec["id"]),
            "goal": goal,
            "premises": premises,
        })
        if verbose:
            print(f"+ {new_id} {rec.get('name','')}: "
                  f"{goal} :- {premises}")

    # 不够 target，从 theorems/*.jsonl 补
    if len(cases) + len(added) < target:
        import glob
        for path in sorted(glob.glob(os.path.join(ROOT, "theorems", "*.jsonl"))):
            if len(cases) + len(added) >= target:
                break
            base = os.path.basename(path)
            if base in ("12_0_competition.jsonl", "concept_neurons.json"):
                continue
            if "learn_log" in base or "candidates" in base:
                continue
            for rec in load_jsonl(path):
                if len(cases) + len(added) >= target:
                    break
                if not rec.get("head"):
                    continue
                if only_simple and not _is_simple(rec):
                    continue
                goal = rec["head"]
                premises = rec.get("body", [])
                sig = _norm(goal, premises)
                if sig in seen:
                    continue
                seen.add(sig)
                new_id = f"X{next_n:03d}"
                next_n += 1
                added.append({
                    "id": new_id,
                    "statement": rec.get("name", rec.get("id", "")),
                    "goal": goal,
                    "premises": premises,
                })
                if verbose:
                    print(f"+ {new_id} [定理库] {rec.get('name','')}: "
                          f"{goal} :- {premises}")

    if dry_run:
        print(f"[dry] 现有 {len(cases)}，可加 {len(added)}，"
              f"目标 {target}")
        return len(added)

    with open(cases_path, "a", encoding="utf-8") as f:
        for c in added:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"[expand] 现有 {len(cases)} + 新增 {len(added)} = "
          f"{len(cases) + len(added)}")
    return len(added)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=200)
    ap.add_argument("--only-simple", action="store_true",
                    help="只加 13.x 已支持谓词的题（pass 率稳 ≥95%）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    expand(args.target, args.only_simple, args.dry_run, args.verbose)