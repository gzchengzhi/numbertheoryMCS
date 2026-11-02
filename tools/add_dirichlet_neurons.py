# tools/add_dirichlet_neurons.py
import json, os, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

path = "domains/dirichlet/concept_neurons.json"
shutil.copy2(path, path + ".bak")

with open(path, encoding="utf-8") as f:
    data = json.load(f)

NEW = {
    # C098
    "NEURON::S::equals<-dirichlet_character::arity=1": {
        "neuron_id": "NEURON::S::equals<-dirichlet_character::arity=1",
        "type": "single",
        "lower": [["dirichlet_character", ["chi", "m"]]],
        "mediator": None,
        "anchor": None,
        "head_pattern": ["equals", ["chi(1)", "1"]],
        "N": 1, "weight": 1.0, "instances": [],
    },
    # C099
    "NEURON::S::equals<-dirichlet_character::arity=1::multiplicative": {
        "neuron_id": "NEURON::S::equals<-dirichlet_character::arity=1::multiplicative",
        "type": "single",
        "lower": [["dirichlet_character", ["chi", "m"]]],
        "mediator": None,
        "anchor": None,
        "head_pattern": ["equals", ["chi(times(a,b))", "times(chi(a), chi(b))"]],
        "N": 1, "weight": 1.0, "instances": [],
    },
    # C100
    "NEURON::SP::equals<-dirichlet_character+gt::arity=1": {
        "neuron_id": "NEURON::SP::equals<-dirichlet_character+gt::arity=1",
        "type": "shared_param",
        "lower": [["dirichlet_character", ["chi", "m"]], ["gt", ["gcd(a,m)", "1"]]],
        "mediator": None,
        "anchor": "m",
        "head_pattern": ["equals", ["chi(a)", "0"]],
        "N": 1, "weight": 1.0, "instances": [],
    },
    # C101
    "NEURON::SP::equals<-dirichlet_character+not_principal::arity=1": {
        "neuron_id": "NEURON::SP::equals<-dirichlet_character+not_principal::arity=1",
        "type": "shared_param",
        "lower": [
            ["dirichlet_character", ["chi", "m"]],
            ["not", ["is_principal_character(chi)"]]
        ],
        "mediator": None,
        "anchor": "m",
        "head_pattern": ["equals", ["sum(a,1,m,chi(a))", "0"]],
        "N": 1, "weight": 1.0, "instances": [],
    },
    # C102
    "NEURON::S::forall<-coprime+gt::arity=1": {
        "neuron_id": "NEURON::S::forall<-coprime+gt::arity=1",
        "type": "single",
        "lower": [["coprime", ["a", "m"]], ["gt", ["m", "1"]]],
        "mediator": None,
        "anchor": None,
        "head_pattern": ["forall", ["N", "exists(p, and(prime(p), and(gt(p,N), congruent(p,a,m))))"]],
        "N": 1, "weight": 1.0, "instances": [],
    },
}

added, updated = [], []
for nid, neuron in NEW.items():
    if nid in data["concept_neurons"]:
        data["concept_neurons"][nid] = neuron
        updated.append(nid)
    else:
        data["concept_neurons"][nid] = neuron
        added.append(nid)

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"added: {added}")
print(f"updated: {updated}")
print(f"total: {len(data['concept_neurons'])}")