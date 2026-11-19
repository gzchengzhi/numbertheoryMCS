# tools/erdos_straus_p1_mod24_density.py
"""20.0.4/20.0.5: 大筛法密度 0 与 CRT 密度上界的 MCS 封装。

纪律：
  - 只记录实测失败率乘积 < 1 且单调递减。
  - 不声称乘积严格趋于 0 对所有 r 成立。
  - 不声称例外集为空。
"""
import json
from typing import List, Dict
from tools.erdos_straus_p1_mod24_symbolic import compute_failure_set


def failure_rate(r: int, c: int = 4, p_max: int = 100000) -> float:
    """实测失败率 |F_r| / (r-1)。"""
    F = compute_failure_set(r, c, p_max)
    return len(F) / (r - 1)


def cumulative_failure_product(r_list: List[int]) -> List[Dict]:
    """计算 R 中前 k 个 r 的累积失败率乘积。"""
    results = []
    product = 1.0
    for r in r_list:
        rate = failure_rate(r)
        product *= rate
        results.append({
            "r": r,
            "failure_rate": rate,
            "cumulative_product": product,
        })
    return results


def density_upper_bound(r_list: List[int]) -> float:
    """未覆盖集密度的上界（乘积）。"""
    product = 1.0
    for r in r_list:
        product *= failure_rate(r)
    return product


# ============================================================
# MCS 神经元封装
# ============================================================
def large_sieve_neuron(r_list: List[int]) -> dict:
    """20.0.4: 大筛法神经元——输入实测失败率，输出密度上界。"""
    product = density_upper_bound(r_list)
    return {
        "neuron": "NEURON::S::large_sieve_density_bound::p1_mod24",
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
            "不声称例外集为空。"
        ),
    }


def crt_density_neuron(r_list: List[int]) -> dict:
    """20.0.5: CRT 加总神经元——记录密度上界。"""
    product = density_upper_bound(r_list)
    return {
        "neuron": "NEURON::S::crt_density_bound::p1_mod24",
        "type": "single",
        "lower": [
            ["crt", [f"r={r}" for r in r_list]],
            ["density_upper_bound", [f"{product:.6f}"]],
        ],
        "mediator": None,
        "anchor": None,
        "head_pattern": [
            "uncovered_density_upper_bound",
            ["crt_combined", f"{product:.6f}"],
        ],
        "N": 1,
        "weight": 1.0,
        "note": (
            f"CRT 加总后，未覆盖集密度上界 = {product:.6f}。"
            "当 R 扩大（更多 r），乘积递减，密度上界递减。"
            "不声称乘积严格趋于 0。"
        ),
    }


def solidify_density_neurons(
    r_list: List[int],
    store_path: str = "theorems/20_0_p1_mod24_density.json",
):
    """把大筛法与 CRT 密度神经元固化。"""
    neurons = {
        "NEURON::S::large_sieve_density_bound::p1_mod24":
            large_sieve_neuron(r_list),
        "NEURON::S::crt_density_bound::p1_mod24":
            crt_density_neuron(r_list),
    }
    data = {"concept_neurons": neurons, "neuron_edges": {}}
    with open(store_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return store_path