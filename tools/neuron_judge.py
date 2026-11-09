"""
14.0.5c: 神经元判定扩展（B 方案：组合 learn_12_0.judge，learn_12_0.py 零改动）。

契约与 learn_12_0.judge 严格同构：
    judge(rec) -> (decision, reason)，decision ∈ {"keep", "drop"}

行为：
- 默认先调 learn_12_0.judge(rec)
- 若返回 keep -> 直接返回（规则认可）
- 若返回 drop，且命中以下任一扩展条件，覆盖为 keep：
    * lower 里含 NEURON:: 引用（递归点火神经元）
    * N >= 2（深度神经元）
- 其余情况原样返回 learn_12_0.judge 的结果

这样：
- 非 NEURON:: 非 N>=2 的输入，逐字节等于 learn_12_0.judge
- learn_12_0.py 不动，131 不变
- 13.x 的 PRED_BAD / weak_single_hp_none 等规则仍然生效（因为先走 learn_12_0.judge，
  只有当它 drop 且命中扩展条件时才覆盖）
"""
from typing import Tuple, Dict

# 延迟导入，避免循环（learn_12_0 顶层 import concept_triangle / sympy_bridge，
# 这里只是函数内 import，无循环风险）
def _rules_judge(rec: Dict) -> Tuple[str, str]:
    from tools.learn_12_0 import judge as rules_judge
    return rules_judge(rec)


def _has_neuron_lower(rec: Dict) -> bool:
    """lower 里是否有 NEURON:: 引用（二元组或裸字符串）。"""
    for low in rec.get("lower") or []:
        if isinstance(low, str) and low.startswith("NEURON::"):
            return True
        if (isinstance(low, (list, tuple)) and len(low) >= 1
                and isinstance(low[0], str) and low[0].startswith("NEURON::")):
            return True
    return False


def _n_ge_2(rec: Dict) -> bool:
    try:
        return int(rec.get("N", 1)) >= 2
    except (TypeError, ValueError):
        return False


def judge(rec: Dict) -> Tuple[str, str]:
    """返回 (decision, reason)。decision ∈ {"keep", "drop"}。"""
    decision, reason = _rules_judge(rec)
    if decision == "keep":
        return decision, reason

    # 规则 drop，检查扩展条件
    if _has_neuron_lower(rec):
        return "keep", "neuron_lower_override"
    if _n_ge_2(rec):
        return "keep", "n_ge_2_override"

    return decision, reason