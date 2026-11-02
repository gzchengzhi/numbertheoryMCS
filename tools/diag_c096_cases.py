# tools/diag_c096_cases.py
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

with open("tests/bench/competition/cases.jsonl", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            rec = json.loads(line)
            if rec["id"] == "C096":
                print(f"goal: {rec['goal']}")
                print(f"premises: {rec.get('premises')}")