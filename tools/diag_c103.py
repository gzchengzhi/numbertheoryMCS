# tools/diag_c103.py
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

# bench_competition 的 C103
with open("tests/bench/competition/cases.jsonl", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            rec = json.loads(line)
            if rec["id"] in ("C103", "C104", "C105", "C106", "C107"):
                print(f"[competition] {rec['id']}: goal={rec['goal']}")
                print(f"              premises={rec.get('premises')}")

# domains/elliptic 的 C103
with open("domains/elliptic/cases.jsonl", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            rec = json.loads(line)
            print(f"[elliptic] {rec['id']}: goal={rec['goal']}")
            print(f"           premises={rec.get('premises')}")