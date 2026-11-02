# tools/merge_c096_flat_and.py
"""13.0.5：用扁平 and 的 C096 神经元替换旧的 S::pythagorean。"""
import json, os, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

path = "theorems/concept_neurons.json"
shutil.copy2(path, path + ".bak_c096_flat_and")

with open(path, encoding="utf-8") as f:
    data = json.load(f)

# 删旧的 S::pythagorean
old_nid = "NEURON::S::pythagorean<-exists::arity=3"
if old_nid in data["concept_neurons"]:
    del data["concept_neurons"][old_nid]
    print(f"[del] {old_nid}")

# 加扁平的 C096 神经元
new_nid = "NEURON::S::exists<-c096_pythagorean::arity=1"
data["concept_neurons"][new_nid] = {
    "neuron_id": new_nid,
    "type": "single",
    "lower": [
        ["equals", ["plus(power(a,2),power(b,2))", "power(c,2)"]],
        ["gt", ["a", "0"]],
        ["gt", ["b", "0"]],
        ["gt", ["c", "0"]]
    ],
    "mediator": None,
    "anchor": None,
    "head_pattern": [
        "exists",
        ["m", "exists(n, and(gt(m,n), coprime(m,n), equals(a, minus(power(m,2),power(n,2))), equals(b, times(2,times(m,n))), equals(c, plus(power(m,2),power(n,2)))))"]
    ],
    "N": 1,
    "weight": 1.0,
    "instances": []
}
print(f"[add] {new_nid}")

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"[done] 写入 {path}, 总神经元: {len(data['concept_neurons'])}")