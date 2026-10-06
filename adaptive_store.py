"""
自适应定理库：动态权重 + 启发式检索
"""

import json
import os
from collections import defaultdict
from typing import List, Dict, Set, Optional

from numtheory_prover import HornClause, Pred, Const, Var
from theorem_store import TheoremStore


WEIGHT_FILE = "theorem_weights.json"
MIN_WEIGHT = 0.1
MAX_WEIGHT = 2.0
ALPHA = 0.1       # 成功强化
BETA = 0.05       # 失败弱化


class AdaptiveStore(TheoremStore):
    """在 TheoremStore 基础上加权重学习和自适应检索"""

    def __init__(self):
        # 共现边：(T_i, T_j) → 权重
        self.cooccur_edges: Dict[tuple, float] = defaultdict(lambda: 1.0)
        super().__init__()
        self.theorem_weights: Dict[str, float] = defaultdict(lambda: 1.0)
        self.usage_stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"used": 0, "success": 0, "fail": 0})

    # ============================================================
    # 打分核心
    # ============================================================
    def _score_all(self, goal: Pred) -> Dict[str, float]:
        """对所有定理打分"""
        goal_pred = goal.name
        goal_consts = self._extract_consts(goal)
        scores: Dict[str, float] = defaultdict(float)

        for c in self.clauses:
            s = 0.0
            # head 谓词匹配
            if c.head.name == goal_pred:
                s += 10.0
                head_consts = self._extract_consts(c.head)
                s += 5.0 * len(goal_consts & head_consts)
            # body 谓词匹配
            for b in c.body:
                if b.name == goal_pred:
                    s += 3.0
                    body_consts = self._extract_consts(b)
                    s += 2.0 * len(goal_consts & body_consts)
            if s > 0:
                scores[c.id] = s
        return scores

    def _extract_consts(self, pred: Pred) -> Set[str]:
        """从谓词里抽所有常量"""
        result = set()
        def walk(t):
            if isinstance(t, Const):
                if not t.args:
                    result.add(t.name)
                for a in t.args:
                    walk(a)
        for a in pred.args:
            walk(a)
        return result

    # ============================================================
    # 权重持久化
    # ============================================================
    def load_weights(self, path: str = WEIGHT_FILE):
        if not os.path.exists(path):
            return
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for tid, w in data.get("weights", {}).items():
            self.theorem_weights[tid] = w
        for tid, s in data.get("stats", {}).items():
            self.usage_stats[tid] = s
            # 共现边
        for key, w in data.get("cooccur_edges", {}).items():
            parts = key.split("|")
            if len(parts) == 2:
                self.cooccur_edges[(parts[0], parts[1])] = w

    def save_weights(self, path: str = WEIGHT_FILE):
        # 共现边序列化：(a, b) → "a|b"
        edges_serializable = {
            f"{a}|{b}": w for (a, b), w in self.cooccur_edges.items()
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                "weights": dict(self.theorem_weights),
                "stats": {k: dict(v) for k, v in self.usage_stats.items()},
                "cooccur_edges": edges_serializable,     # ← 加在这里
            }, f, ensure_ascii=False, indent=2)
            
        # 共现边
        edges_serializable = {
            f"{a}|{b}": w for (a, b), w in self.cooccur_edges.items()
        }

    # ============================================================
    # 权重更新
    # ============================================================
    def strengthen(self, theorem_ids: List[str]):
        """成功路径强化"""
        for tid in theorem_ids:
            w = self.theorem_weights[tid]
            self.theorem_weights[tid] = min(MAX_WEIGHT, w + ALPHA)
            self.usage_stats[tid]["used"] += 1
            self.usage_stats[tid]["success"] += 1
            if tid not in self.by_id:
                continue

    def weaken(self, theorem_ids: List[str]):
        """失败路径弱化"""
        for tid in theorem_ids:
            w = self.theorem_weights[tid]
            self.theorem_weights[tid] = max(MIN_WEIGHT, w - BETA)
            self.usage_stats[tid]["used"] += 1
            self.usage_stats[tid]["fail"] += 1
            if tid not in self.by_id:
                continue

    # ============================================================
    # 自适应检索
    # ============================================================
    def retrieve_adaptive(self, goal: Pred, top_k: int = 20,
                          expand_round: int = 0,
                          excluded_ids: Set[str] = None
                          ) -> List[HornClause]:
        """
        expand_round: 0=直接匹配，1=扩展一步，2=扩展两步
        excluded_ids: 已尝试失败的定理，不重复检索
        """
        if excluded_ids is None:
            excluded_ids = set()

        # 1. 基础打分
        scores = self._score_all(goal)

        # 2. 权重调整
        for cid in list(scores.keys()):
            scores[cid] *= self.theorem_weights[cid]

        # 3. 闭包扩展（每轮多扩一层）
        for _ in range(expand_round):
            new_preds = set()
            for cid in list(scores.keys()):
                c = self.by_id[cid]
                for b in c.body:
                    new_preds.add(b.name)
            for pred_name in new_preds:
                for cid in self.by_predicate.get(pred_name, []):
                    if cid not in scores and cid not in excluded_ids:
                        scores[cid] = 0.5 * self.theorem_weights[cid]
                    elif cid in scores:
                        scores[cid] += 0.5

        # 3.5 共现边扩展（每轮都跑）
        current_ids = list(scores.keys())
        for cid in current_ids:
            for neighbor_id, w in self.get_cooccur_neighbors(cid, threshold=1.2):
                if neighbor_id in excluded_ids:
                    continue
                if neighbor_id not in scores:
                    scores[neighbor_id] = 5.0 * (w - 1.0)
                else:
                    scores[neighbor_id] += 2.0 * (w - 1.0)

        # 4. 排除已失败
        for cid in excluded_ids:
            scores.pop(cid, None)

        # 5. 排序
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        result_ids = [cid for cid, _ in ranked[:top_k]]
        return [self.by_id[cid] for cid in result_ids]

    # ============================================================
    # 权重统计
    # ============================================================
    def weight_stats(self) -> Dict:
        ws = list(self.theorem_weights.values())
        edges = list(self.cooccur_edges.values())
        return {
            "平均权重": round(sum(ws) / max(len(ws), 1), 3),
            "最高权重": round(max(ws), 3) if ws else 0,
            "最低权重": round(min(ws), 3) if ws else 0,
            "已学习定理数": sum(1 for w in ws if w != 1.0),
            "共现边数": len(self.cooccur_edges),
            "强共现边数(>1.5)": sum(1 for w in edges if w > 1.5),
        }
    # ============================================================
    # 共现边学习
    # ============================================================
    def learn_cooccurrence(self, used_ids: List[str], alpha: float = 0.15):
        """证明成功后，强化链上所有定理对的共现边"""
        ids = [tid for tid in used_ids if tid in self.by_id]
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                if a == b:
                    continue
                key = (a, b) if a < b else (b, a)
                self.cooccur_edges[key] = min(MAX_WEIGHT,
                                              self.cooccur_edges[key] + alpha)
    
    def weaken_cooccurrence(self, attempted_ids: List[str], beta: float = 0.05):
        """失败路径弱化"""
        ids = [tid for tid in attempted_ids if tid in self.by_id]
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                if a == b:
                    continue
                key = (a, b) if a < b else (b, a)
                self.cooccur_edges[key] = max(MIN_WEIGHT,
                                              self.cooccur_edges[key] - beta)
    
    def get_cooccur_neighbors(self, tid: str, threshold: float = 1.2,
                              max_neighbors: int = 10) -> List[tuple]:
        """给定定理 id，返回强共现的邻居 [(other_id, edge_weight), ...]"""
        neighbors = []
        for (a, b), w in self.cooccur_edges.items():
            if w <= threshold:
                continue
            if a == tid:
                neighbors.append((b, w))
            elif b == tid:
                neighbors.append((a, w))
        neighbors.sort(key=lambda x: x[1], reverse=True)
        return neighbors[:max_neighbors]