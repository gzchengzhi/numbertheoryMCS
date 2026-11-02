# tools/append_cases.py
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
path = "tests/bench/competition/cases.jsonl"

NEW = [
    # 上面 30 条 C051~C080
    
]

existing = set()
with open(path, encoding="utf-8") as f:
    for line in f:
        if line.strip():
            existing.add(json.loads(line)["id"])

# 确保末尾有换行
with open(path, "rb") as f:
    f.seek(-1, 2)
    if f.read(1) != b"\n":
        with open(path, "a", encoding="utf-8") as f2:
            f2.write("\n")

with open(path, "a", encoding="utf-8") as f:
    for t in NEW:
        if t["id"] in existing:
            print(f"skip {t['id']}")
        else:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
            print(f"+ {t['id']}")