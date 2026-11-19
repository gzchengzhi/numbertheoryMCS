# tools/erdos_straus_p1_mod24_neurons.py
"""20.8: 将论文的代数推导构造为 MCS 概念神经元。"""
import json

def build_proof_neurons():
    neurons = {
        # 底层：分支方程的定义
        "NEURON::S::branch_equation_p1_mod24": {
            "neuron_id": "NEURON::S::branch_equation_p1_mod24",
            "type": "single",
            "lower": [["prime", ["p", "1", "24"]], ["prime", ["r", "3", "4"]]],
            "mediator": None,
            "anchor": None,
            "head_pattern": ["branch_equation", ["4/p", "4/(p+r)", "r/(pq)"]],
            "N": 1,
            "weight": 1.0,
            "note": "Definition: 4/p = 4/(p+r) + r/(pq), where q=(p+r)/4."
        },
        # 第一层：转化为因子同余条件
        "NEURON::S::success_criterion_congruence": {
            "neuron_id": "NEURON::S::success_criterion_congruence",
            "type": "single",
            "lower": [["branch_equation", ["4/p", "4/(p+r)", "r/(pq)"]]],
            "mediator": None,
            "anchor": None,
            "head_pattern": ["exists_d", ["d|p^2q^2", "d ≡ -pq (mod r)"]],
            "N": 1,
            "weight": 1.0,
            "note": "Standard two-denominator criterion."
        },
        # 第二层：化简同余式
        "NEURON::S::simplified_congruence": {
            "neuron_id": "NEURON::S::simplified_congruence",
            "type": "single",
            "lower": [["exists_d", ["d|p^2q^2", "d ≡ -pq (mod r)"]]],
            "mediator": None,
            "anchor": None,
            "head_pattern": ["simplified", ["d ≡ -4q^2 (mod r)"]],
            "N": 1,
            "weight": 1.0,
            "note": "Substitute p ≡ 4q (mod r)."
        },
        # 第三层：枚举 9 个因子，消去 q^2
        "NEURON::S::dangerous_classes": {
            "neuron_id": "NEURON::S::dangerous_classes",
            "type": "single",
            "lower": [["simplified", ["d ≡ -4q^2 (mod r)"]]],
            "mediator": None,
            "anchor": None,
            "head_pattern": ["three_conditions", ["q ≡ -1", "q ≡ -1/4", "q^2 ≡ -1/4 (mod r)"]],
            "N": 1,
            "weight": 1.0,
            "note": "Enumerate d = p^a q^b for 0<=a,b<=2. Only three independent equations."
        },
        # 第四层：翻译回 p 的条件
        "NEURON::S::translate_to_p": {
            "neuron_id": "NEURON::S::translate_to_p",
            "type": "single",
            "lower": [["three_conditions", ["q ≡ -1", "q ≡ -1/4", "q^2 ≡ -1/4 (mod r)"]]],
            "mediator": None,
            "anchor": None,
            "head_pattern": ["three_conditions_p", ["p ≡ -4", "p ≡ -1", "p^2 ≡ -4 (mod r)"]],
            "N": 1,
            "weight": 1.0,
            "note": "Translate q back to p."
        },
        # 第五层：二次互反律排除 p^2 ≡ -4
        "NEURON::S::quadratic_reciprocity_exclusion": {
            "neuron_id": "NEURON::S::quadratic_reciprocity_exclusion",
            "type": "single",
            "lower": [["three_conditions_p", ["p ≡ -4", "p ≡ -1", "p^2 ≡ -4 (mod r)"]], ["prime", ["r", "3", "4"]]],
            "mediator": None,
            "anchor": None,
            "head_pattern": ["exclude", ["p^2 ≡ -4 (mod r)"]],
            "N": 1,
            "weight": 1.0,
            "note": "(-4/r) = (-1/r)(4/r) = (-1)(1) = -1. No solution."
        },
        # 第六层：最终结论
        "NEURON::S::final_divisibility": {
            "neuron_id": "NEURON::S::final_divisibility",
            "type": "single",
            "lower": [["three_conditions_p", ["p ≡ -4", "p ≡ -1", "p^2 ≡ -4 (mod r)"]], ["exclude", ["p^2 ≡ -4 (mod r)"]]],
            "mediator": None,
            "anchor": None,
            "head_pattern": ["final_reduction", ["r | p+4", "r | p+1"]],
            "N": 1,
            "weight": 1.0,
            "note": "Success strictly equivalent to r | p+4 or r | p+1."
        },
        # 第七层：反例的 S-单位方程形式
        "NEURON::S::counterexample_S_unit": {
            "neuron_id": "NEURON::S::counterexample_S_unit",
            "type": "single",
            "lower": [["final_reduction", ["r | p+4", "r | p+1"]], ["no_small_r", ["r < p"]]],
            "mediator": None,
            "anchor": None,
            "head_pattern": ["S_unit_equation", ["u2 - 2u1 = 3"]],
            "N": 1,
            "weight": 1.0,
            "note": "If no r < p succeeds, then p+1 and p+4 have only 1 mod 4 prime factors. Let p+1=2u1, p+4=u2."
        }
    }

    data = {
        "concept_neurons": neurons,
        "neuron_edges": {
            # 定义概念之间的激活关系
            "branch_equation_p1_mod24": ["success_criterion_congruence"],
            "success_criterion_congruence": ["simplified_congruence"],
            "simplified_congruence": ["dangerous_classes"],
            "dangerous_classes": ["translate_to_p"],
            "translate_to_p": ["quadratic_reciprocity_exclusion"],
            "quadratic_reciprocity_exclusion": ["final_divisibility"],
            "final_divisibility": ["counterexample_S_unit"]
        }
    }

    with open("theorems/20_8_proof_neurons.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("MCS 推导神经元已固化到 theorems/20_8_proof_neurons.json")

if __name__ == "__main__":
    build_proof_neurons()