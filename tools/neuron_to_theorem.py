# tools/neuron_to_theorem.py
"""15.0.2 NEURON::xxx → HornClause 转换器。

输入：theorems/concept_neurons.json 里的 concept_neurons
输出：List[HornClause]，可写入 theorems/15_0_from_neurons.jsonl

纪律：
  - 只转有 head_pattern 的神经元（head_pattern is None 跳过）
  - lower 里的 NEURON::xxx 递归转（无 head 的神经元跳过整条）
  - head_pattern 用 parse_term 解析（13.x 规则：纯数字→Const，单字母→Var）
  - and 保留原样（15.0.2 不做扁平化，verify 走 to_sympy）
  - 生成的 HornClause.category = "自动发现"
"""
import json
import os
from typing import Dict, List, Optional, Set

from numtheory_prover import (
    HornClause, Pred, Var, Const, parse_term,
)


# ============================================================
# 核心转换
# ============================================================
class NeuronToTheorem:
    def __init__(self, neurons: Dict[str, Dict], verbose: bool = False):
        self.neurons = neurons
        self.verbose = verbose
        self._cache: Dict[str, Optional[HornClause]] = {}

    def convert_all(self) -> List[HornClause]:
        """转换所有有 head_pattern 的神经元。

        返回：List[HornClause]，id 形如 NEURON_TO_THM::<neuron_id>
        """
        result = []
        for nid in self.neurons:
            clause = self.convert(nid)
            if clause is not None:
                result.append(clause)
        if self.verbose:
            print(f"[neuron_to_theorem] {len(result)}/{len(self.neurons)} "
                  f"神经元转成定理")
        return result

    def convert(self, nid: str) -> Optional[HornClause]:
        """单个神经元转换。无 head_pattern 或 lower 不可转 → None。"""
        if nid in self._cache:
            return self._cache[nid]

        neuron = self.neurons.get(nid)
        if neuron is None:
            self._cache[nid] = None
            return None

        hp = neuron.get("head_pattern")
        if hp is None:
            if self.verbose:
                print(f"[skip] {nid}: head_pattern is None")
            self._cache[nid] = None
            return None

        # 1. head_pattern → Pred
        head = self._parse_head_pattern(hp)
        if head is None:
            if self.verbose:
                print(f"[skip] {nid}: head_pattern 解析失败 {hp!r}")
            self._cache[nid] = None
            return None

        # 2. lower → List[Pred]
        #    先标记正在转换，防环
        self._cache[nid] = None  # 占位，防自引用
        body: List[Pred] = []
        for low in neuron.get("lower", []):
            pred = self._parse_lower(low, nid)
            if pred is None:
                if self.verbose:
                    print(f"[skip] {nid}: lower 不可转 {low!r}")
                self._cache[nid] = None
                return None
            body.append(pred)

        # 3. 构造 HornClause
        clause = HornClause(
            id=f"NEURON_TO_THM::{nid}",
            name=f"自动发现 {nid}",
            head=head,
            body=body,
            category="自动发现",
        )
        self._cache[nid] = clause
        return clause

    # ============================================================
    # head_pattern → Pred
    # ============================================================
    def _parse_head_pattern(self, hp) -> Optional[Pred]:
        if isinstance(hp, str):
            # 形如 "divides(a, c)"
            from numtheory_prover import parse_goal
            return parse_goal(hp)
        if isinstance(hp, (list, tuple)) and len(hp) >= 2:
            name = hp[0]
            args = hp[1]
            if not isinstance(args, (list, tuple)):
                return None
            parsed_args = []
            for a in args:
                t = self._parse_arg(a)
                if t is None:
                    return None
                parsed_args.append(t)
            return Pred(name, tuple(parsed_args))
        return None

    def _parse_arg(self, a):
        """把 head_pattern 的 arg 转成项。

        规则与 13.x parse_term 一致：
          - 纯数字 "1" → Const("1")
          - 单字母 "a" → Var("a")
          - 含 "(" 如 "power(p,2)" → parse_term
          - 其他 → Const(a)
        """
        if not isinstance(a, str):
            return None
        a = a.strip()
        if "(" in a:
            return parse_term(a)
        if a.lstrip("-").isdigit():
            return Const(a)
        # 单字母（含大小写）→ Var；多字母小写 → Var（13.x DEFAULT_VAR_NAMES）
        if len(a) == 1 and a.isalpha():
            return Var(a)
        # 多字母：x1, n2, d1, m1, m2, a_i 等 → Var（13.x 的 DEFAULT_VAR_NAMES 没包含它们，
        # 但 concept_triangle 的 _is_var 认 [a-z]\d*，这里对齐）
        import re
        if re.match(r'^[a-z]\d*$', a):
            return Var(a)
        return Const(a)

    # ============================================================
    # lower → Pred
    # ============================================================
    def _parse_lower(self, low, parent_nid: str) -> Optional[Pred]:
        """lower 有两种形态：
          - ["pred_name", ["arg1", "arg2"]] → Pred
          - "NEURON::xxx" → 递归转该神经元，取其 head
        """
        if isinstance(low, str) and low.startswith("NEURON::"):
            sub_clause = self.convert(low)
            if sub_clause is None:
                return None
            return sub_clause.head

        if isinstance(low, (list, tuple)) and len(low) >= 2:
            name = low[0]
            args = low[1]
            if not isinstance(args, (list, tuple)):
                return None
            parsed_args = []
            for a in args:
                t = self._parse_arg(a)
                if t is None:
                    return None
                parsed_args.append(t)
            return Pred(name, tuple(parsed_args))

        return None


# ============================================================
# 便捷入口
# ============================================================
def load_neurons(path: str = "theorems/concept_neurons.json") -> Dict[str, Dict]:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("concept_neurons", {})


def convert_file(path: str = "theorems/concept_neurons.json",
                 verbose: bool = False) -> List[HornClause]:
    neurons = load_neurons(path)
    return NeuronToTheorem(neurons, verbose=verbose).convert_all()


def save_jsonl(clauses: List[HornClause],
               path: str = "theorems/15_0_from_neurons.jsonl"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for c in clauses:
            rec = {
                "id": c.id,
                "name": c.name,
                "category": c.category,
                "head": str(c.head),
                "body": [str(b) for b in c.body],
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[save] {len(clauses)} 条写入 {path}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp",
                    default="theorems/concept_neurons.json")
    ap.add_argument("--out", dest="out",
                    default="theorems/15_0_from_neurons.jsonl")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    clauses = convert_file(args.inp, verbose=args.verbose)
    save_jsonl(clauses, args.out)