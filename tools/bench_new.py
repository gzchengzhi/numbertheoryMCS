# tools/bench_new.py
"""17.0.4 新题 benchmark：50 道新题，diagnose --auto-learn，pass 率 ≥ 90%。"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_new_cases(path="tests/bench/competition/new_cases.jsonl"):
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def run_bench(auto_learn=True):
    from tools.bench_competition import make_rp
    from tools.diagnose import diagnose
    cases = load_new_cases()
    if not cases:
        print(f"[new] 无新题，先跑 tools/gen_new_cases.py")
        return

    counts = {"total": 0, "pass": 0, "fail": 0, "auto_learned": 0}
    for case in cases:
        counts["total"] += 1
        rp = make_rp()
        proof = rp.prove(case["goal"],
                         premises=case.get("premises", []),
                         verbose=False)
        if proof is not None:
            counts["pass"] += 1
            print(f"[OK] {case['id']}: {case['goal']}")
            continue
        if auto_learn:
            rc = diagnose(case["goal"], case.get("premises", []),
                          auto_learn=True, make_rp_fn=make_rp)
            if rc == 0:
                counts["pass"] += 1
                counts["auto_learned"] += 1
                print(f"[AUTO] {case['id']}: {case['goal']}")
            else:
                counts["fail"] += 1
                print(f"[FAIL] {case['id']}: {case['goal']}")
        else:
            counts["fail"] += 1
            print(f"[FAIL] {case['id']}: {case['goal']}")

    rate = 100 * counts["pass"] // max(counts["total"], 1)
    print(f"\n[new] {counts['pass']}/{counts['total']} ({rate}%)，"
          f"auto_learned={counts['auto_learned']}")
    return counts


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-auto", action="store_true")
    args = ap.parse_args()
    run_bench(auto_learn=not args.no_auto)