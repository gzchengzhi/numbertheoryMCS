# tools/erdos_straus_p1_mod24_extend_solidify.py
"""20.1: 固化扩展 R 的 F_r 与乘积。"""
import json
from tools.erdos_straus_p1_mod24_symbolic import compute_failure_set
from tools.erdos_straus_p1_mod24_density import failure_rate, density_upper_bound


def solidify_extended(store_path: str = "theorems/20_1_p1_mod24_density.json"):
    r_list = [3, 7, 11, 23, 31, 43, 47, 59, 67, 71, 79, 83]
    neurons = {}
    for r in r_list:
        F = compute_failure_set(r)
        nid = f"NEURON::S::failure_set_p1_mod24_ext::r={r}"
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
    product = density_upper_bound(r_list)
    neurons["NEURON::S::large_sieve_density_bound_ext::p1_mod24"] = {
        "neuron": "NEURON::S::large_sieve_density_bound_ext::p1_mod24",
        "type": "single",
        "lower": [
            ["large_sieve", ["gallagher"]],
            ["failure_rate_lt_one", [f"r={r}" for r in r_list]],
        ],
        "mediator": None,
        "anchor": None,
        "head_pattern": [
            "uncovered_density_upper_bound",
            [f"R={r_list}", f"product={product:.6f}"],
        ],
        "N": 1,
        "weight": 1.0,
        "note": (
            f"实测失败率乘积 = {product:.6f} < 1。"
            "根据 Gallagher 大筛法，未覆盖集密度被该乘积控制。"
            "不声称例外集为空，不声称乘积严格趋于 0。"
        ),
    }
    data = {"concept_neurons": neurons, "neuron_edges": {}}
    with open(store_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return store_path, product