# deep_proof.py
"""15.0 深递归证明步骤（树形，保留子目标 + 能量账本）。

与 13.x ProofStep 的差异：
  - subgoals: 子目标树（13.x 是扁平 List[ProofStep]）
  - energy_cost: 本步能量消耗（Cheng 2019 §8.5.1，δ = 0.5**depth）
  - energy_left: 本步后剩余能量（总预算 - 已消耗）
  - depth: 概念三角形层次（复用 13.x 的 depth 语义）
  - strategy: neuron:xxx / iso:xxx / subgoal_split / construct

纪律：
  - 不修改 numtheory_prover.ProofStep
  - to_proof_steps() 降级为扁平 List[ProofStep]，保证 13.x 旧测试零改动通过
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from numtheory_prover import Pred, HornClause


@dataclass
class DeepProofStep:
    clause: HornClause
    substitution: Dict[Any, Any]
    subgoal: Pred
    depth: int
    strategy: str = "deep_chain"
    energy_cost: float = 0.0        # 本步消耗
    energy_left: float = 0.0        # 本步后剩余
    subgoals: List["DeepProofStep"] = field(default_factory=list)

    def flatten(self) -> List["DeepProofStep"]:
        """前序遍历，便于打印和回归比对。"""
        out = [self]
        for s in self.subgoals:
            out.extend(s.flatten())
        return out

    def to_proof_steps(self) -> List:
        """降级为 13.x 扁平 ProofStep，供旧测试复用。"""
        from numtheory_prover import ProofStep
        return [
            ProofStep(s.clause, s.substitution, s.subgoal, s.depth, s.strategy)
            for s in self.flatten()
        ]

    def tree_depth(self) -> int:
        """整棵树的最大概念层次（叶子节点的 depth）。"""
        if not self.subgoals:
            return self.depth
        return max(s.tree_depth() for s in self.subgoals)

    def tree_size(self) -> int:
        """整棵树的节点数。"""
        return 1 + sum(s.tree_size() for s in self.subgoals)

    def total_energy(self) -> float:
        """整棵树的总能量消耗（含子目标）。"""
        return self.energy_cost + sum(s.total_energy() for s in self.subgoals)

    def __repr__(self):
        return (f"DeepProofStep({self.clause.id}, depth={self.depth}, "
                f"strategy={self.strategy}, subgoals={len(self.subgoals)})")