# tools/erdos_straus_p1_mod24_solidify.py
"""20.0: 固化实测 F_r 与大筛密度 0 记录。"""
import json
from tools.erdos_straus_p1_mod24_symbolic import (
    compute_failure_set, density_zero_theorem_record,
)


def solidify_failure_sets(store_path: str = "theorems/20_0_p1_mod24.json"):
    neurons = {}
    for r in [3, 7, 11, 23]:
        F = compute_failure_set(r)
        nid = f"NEURON::S::failure_set_p1_mod24::r={r}"
        neurons[nid] = {
            "neuron_id": nid,
            "type": "single",
            "lower": [["prime", ["r"]], ["congruent", ["r", "3", "4"]]],
            "mediator": None,
            "anchor": None,
            "head_pattern": ["failure_set", [f"r={r}", str(F)]],
            "N": 1,
            "weight": 1.0,
            "note": f"实测 F_{r} = {F}（p_max=100000，实际 p 枚举）",
        }
    rec = density_zero_theorem_record()
    neurons[rec["neuron"]] = rec
    data = {"concept_neurons": neurons, "neuron_edges": {}}
    with open(store_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return store_path