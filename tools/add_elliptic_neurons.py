# tools/add_elliptic_neurons.py
import json, os, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

path = "domains/elliptic/concept_neurons.json"
shutil.copy2(path, path + ".bak")

with open(path, encoding="utf-8") as f:
    data = json.load(f)

NEW = {
    # C103
    "NEURON::S::not<-elliptic_curve::arity=1": {
        "neuron_id": "NEURON::S::not<-elliptic_curve::arity=1",
        "type": "single",
        "lower": [["elliptic_curve", ["E"]]],
        "mediator": None,
        "anchor": None,
        "head_pattern": ["not", ["equals(discriminant_ec(E), 0)"]],
        "N": 1, "weight": 1.0, "instances": [],
    },
    # C104
    "NEURON::S::finitely_generated<-elliptic_curve::arity=1": {
        "neuron_id": "NEURON::S::finitely_generated<-elliptic_curve::arity=1",
        "type": "single",
        "lower": [["elliptic_curve", ["E"]]],
        "mediator": None,
        "anchor": None,
        "head_pattern": ["finitely_generated", ["ec_points(E)"]],
        "N": 1, "weight": 1.0, "instances": [],
    },
    # C105
    "NEURON::S::le<-elliptic_curve::arity=2": {
        "neuron_id": "NEURON::S::le<-elliptic_curve::arity=2",
        "type": "single",
        "lower": [["elliptic_curve", ["E"]]],
        "mediator": None,
        "anchor": None,
        "head_pattern": ["le", ["abs(minus(count_points(E,p), plus(p,1)))", "times(2, sqrt(p))"]],
        "N": 1, "weight": 1.0, "instances": [],
    },
    # C106
    "NEURON::S::equals<-elliptic_curve::arity=2": {
        "neuron_id": "NEURON::S::equals<-elliptic_curve::arity=2",
        "type": "single",
        "lower": [["elliptic_curve", ["E"]]],
        "mediator": None,
        "anchor": None,
        "head_pattern": ["equals", ["add_ec(add_ec(P,Q),R)", "add_ec(P,add_ec(Q,R))"]],
        "N": 1, "weight": 1.0, "instances": [],
    },
    # C107
    "NEURON::S::equals<-elliptic_curve::arity=2::identity": {
        "neuron_id": "NEURON::S::equals<-elliptic_curve::arity=2::identity",
        "type": "single",
        "lower": [["elliptic_curve", ["E"]]],
        "mediator": None,
        "anchor": None,
        "head_pattern": ["equals", ["add_ec(P,infinity)", "P"]],
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