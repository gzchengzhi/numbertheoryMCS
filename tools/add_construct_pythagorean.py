# tools/add_construct_pythagorean.py
import json, os, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
path = "theorems/concept_neurons.json"
shutil.copy2(path, path + ".bak_construct")

with open(path, encoding="utf-8") as f:
    data = json.load(f)

nid = "NEURON::S::pythagorean<-exists::arity=3"
n = data["concept_neurons"].get(nid)
if n:
    n["construct"] = {
        "m": "sqrt(div(plus(c,a), 2))",
        "n": "sqrt(div(minus(c,a), 2))"
    }
    print(f"[{nid}] construct 已加")
else:
    print(f"[MISSING] {nid}")

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"[done] 写入 {path}")