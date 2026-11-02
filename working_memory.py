# D:/BookCode/numbertheoryMCS/working_memory.py
"""
主题指导法（Cheng 2019, 8.5.2）：给定主题线索，只激活相关性最大的神经元。
不消耗 energy —— 抑制发生在点火前，属于注意力路由层。
"""
from typing import Iterable, Optional, Set


class WorkingMemory:
    """
    最小实现：
      - topic: 目标谓词名 + 目标参数中的常量/函数名（主题线索）
      - related_neurons: 预计算的与 topic 相关的神经元 id 集合
      - relevance(nid): 神经元与主题的相关性得分（0~1）
    """

    def __init__(self, topic: str, topic_terms: Iterable[str],
                 related_neurons: Optional[Set[str]] = None):
        self.topic = topic
        self.topic_terms = set(topic_terms)
        self.related_neurons = set(related_neurons or [])

    # ---------- 相关性计算 ----------
    def relevance(self, neuron: dict) -> float:
        """
        神经元与主题的相关性：
          - head_pattern 谓词名命中 topic → +1.0
          - 任一 lower 谓词名命中 topic_terms → +0.5
          - anchor / mediator 出现在 topic_terms → +0.3
        返回 0~1 的归一化得分。
        """
        score = 0.0
        hp = neuron.get("head_pattern")
        if hp:
            hp_name = hp[0] if isinstance(hp, (list, tuple)) else str(hp)
            if hp_name == self.topic:
                score += 1.0

        for low in neuron.get("lower", []):
            if isinstance(low, (list, tuple)) and low:
                if low[0] in self.topic_terms:
                    score += 0.5
            elif isinstance(low, str) and low.startswith("NEURON::"):
                # 子神经元引用：谓词名藏在 id 里
                for term in self.topic_terms:
                    if f"::{term}" in low or f"<{term}" in low or f"+{term}" in low:
                        score += 0.5
                        break

        for key in ("anchor", "mediator"):
            v = neuron.get(key)
            if v and v in self.topic_terms:
                score += 0.3

        return min(score, 1.0)

    # ---------- 过滤 ----------
    def filter_candidates(self, candidates: Iterable[tuple]) -> list:
        """
        candidates: [(nid, weight, type, N), ...]（activate_neuron 的返回格式）
        只保留 relevance > 0 的，并按 relevance 降序稳定排序。
        """
        scored = []
        for item in candidates:
            nid = item[0]
            neuron = self._neuron_of(nid)
            if neuron is None:
                continue
            r = self.relevance(neuron)
            if r > 0.0:
                scored.append((r, item))
        scored.sort(key=lambda x: -x[0])
        return [item for _, item in scored]

    # ---------- 内部 ----------
    def _neuron_of(self, nid):
        # 由 AdaptiveProver 注入 store 引用（见下），避免 WorkingMemory 直接依赖 store
        if getattr(self, "_neuron_lookup", None) is None:
            return None
        return self._neuron_lookup(nid)

    def bind_lookup(self, lookup_fn):
        """AdaptiveProver 构造 WM 时注入 store.concept_neurons 的查表函数"""
        self._neuron_lookup = lookup_fn


class NoopWorkingMemory(WorkingMemory):
    """关闭 WM 时的退化实现：不过滤，退回 10.0 全量匹配"""
    def __init__(self):
        super().__init__(topic="", topic_terms=[])
    def relevance(self, neuron): return 1.0
    def filter_candidates(self, candidates): return list(candidates)


# ---------- 主题提取 ----------
def extract_topic(goal) -> tuple:
    """
    从目标谓词提取主题线索：
      topic        = goal.name
      topic_terms  = goal 参数里出现的所有 Const 名 + 函数名（去重）
    例如 congruent(3,7,2) → ("congruent", {"3","7","2"})
         forall(p, implies(and(prime(p), gt(p,3)), divides(power(p,2), ...)))
           → ("forall", {"p","implies","and","prime","gt","divides","power","3","2"})
    """
    terms = set()
    def walk(t):
        tn = type(t).__name__
        if tn == "Const":
            terms.add(t.name)
            for a in t.args:
                walk(a)
        elif tn == "Pred":
            terms.add(t.name)
            for a in t.args:
                walk(a)
        elif tn == "Var":
            terms.add(t.name)
    for a in goal.args:
        walk(a)
    return goal.name, terms