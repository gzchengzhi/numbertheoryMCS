# tools/fix_c096_cases_flat_and.py
import json, os, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
path = "tests/bench/competition/cases.jsonl"
shutil.copy2(path, path + ".bak_c096_flat")

with open(path, encoding="utf-8") as f:
    lines = [json.loads(l) for l in f if l.strip()]

for rec in lines:
    if rec["id"] == "C096":
        rec["goal"] = "exists(m, exists(n, and(gt(m,n), coprime(m,n), equals(a, minus(power(m,2),power(n,2))), equals(b, times(2,times(m,n))), equals(c, plus(power(m,2),power(n,2))))))"
        print(f"[C096] goal → {rec['goal']}")

with open(path, "w", encoding="utf-8") as f:
    for rec in lines:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
print(f"[done] 写入 {path}")