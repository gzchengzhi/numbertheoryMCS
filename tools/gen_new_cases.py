# tools/gen_new_cases.py
"""17.0.4 生成 50 道新题：从 theorems/*.jsonl 挑未在 cases.jsonl 里的定理。"""
import json
import os
import glob

SIMPLE_PREDS = {
    "divides", "congruent", "equals", "prime", "coprime",
    "gt", "ge", "lt", "le", "odd", "even",
    "quadratic_residue", "nonzero", "sum_to_n",
}

def _pred_of(s):
    return s.split("(", 1)[0].strip()



def _norm(goal, premises):
    return goal + "|" + "|".join(sorted(premises or []))


def main():
    # 已用的题
    used = set()
    with open("tests/bench/competition/cases.jsonl", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            c = json.loads(line)
            used.add(_norm(c["goal"], c.get("premises", [])))

    # 挑新题
    new_cases = []
    seen = set()
    for path in sorted(glob.glob("theorems/*.jsonl")):
        base = os.path.basename(path)
        if base in ("12_0_competition.jsonl", "concept_neurons.json"):
            continue
        if "learn_log" in base or "candidates" in base:
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if not rec.get("head"):
                    continue
                goal = rec["head"]
                premises = rec.get("body", [])                
                # 生成时
                head_pred = _pred_of(goal)
                if head_pred not in SIMPLE_PREDS:
                    continue
                body_preds = [_pred_of(p) for p in premises]
                if not all(p in SIMPLE_PREDS for p in body_preds):
                    continue
                

                sig = _norm(goal, premises)
                if sig in used or sig in seen:
                    continue
                seen.add(sig)
                new_cases.append({
                    "id": f"N{len(new_cases) + 1:03d}",
                    "statement": rec.get("name", rec.get("id", "")),
                    "goal": goal,
                    "premises": premises,
                })
                if len(new_cases) >= 50:
                    break
        if len(new_cases) >= 50:
            break

    with open("tests/bench/competition/new_cases.jsonl", "w",
              encoding="utf-8") as f:
        for c in new_cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"[gen] {len(new_cases)} 道新题写入 new_cases.jsonl")


if __name__ == "__main__":
    main()