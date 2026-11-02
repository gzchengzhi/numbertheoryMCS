# tools/remove_neuron.py
import json, os, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
path = "theorems/concept_neurons.json"
with open(path, encoding="utf-8") as f:
    data = json.load(f)
nid = "NEURON::S::irrational::arity=1"
if nid in data["concept_neurons"]:
    shutil.copy2(path, f".bak/concept_neurons_before_remove_irrational.json")
    del data["concept_neurons"][nid]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 删除 {nid}")
else:
    print(f"⚠️ {nid} 不在")