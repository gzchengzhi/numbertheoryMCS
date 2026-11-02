# tools/fix_pythagorean_construct.py
"""修复 S::pythagorean 的 construct 字段（被 add_neuron_12_10.py 覆盖丢了）。"""
import json, os, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
path = "theorems/concept_neurons.json"
shutil.copy2(path, path + ".bak_pythagorean_construct")

with open(path, encoding="utf-8") as f:
    data = json.load(f)

nid = "NEURON::S::pythagorean<-exists::arity=3"
n = data["concept_neurons"].get(nid)
if n is None:
    print(f"[MISSING] {nid}")
else:
    n["construct"] = {
        "m": "sqrt(div(plus(c,a), 2))",
        "n": "sqrt(div(minus(c,a), 2))"
    }
    print(f"[{nid}] construct 已加")

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"[done] 写入 {path}, 总神经元: {len(data['concept_neurons'])}")