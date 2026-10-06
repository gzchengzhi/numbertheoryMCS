# -*- coding: utf-8 -*-
"""
Created on Tue Oct  6 11:14:57 2026

@author: gzche
"""

"""
定理库管理：从 JSONL 加载、检索、导出
"""

import json
import re
from typing import List, Dict, Set, Optional
from collections import defaultdict

from numtheory_prover import (
    HornClause, Pred, Const, Var, make_pred, make_const, make_var,
    parse_term,
)


class TheoremStore:
    def __init__(self):
        self.clauses: List[HornClause] = []
        self.by_id: Dict[str, HornClause] = {}
        self.by_predicate: Dict[str, List[str]] = defaultdict(list)  # 谓词 → [ids]
        self.by_category: Dict[str, List[str]] = defaultdict(list)

    # ---------- 加载 ----------
    def load_jsonl(self, path: str):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                clause = self._dict_to_clause(obj)
                self.add(clause)

    def _dict_to_clause(self, obj: Dict) -> HornClause:
        head = self._parse_pred(obj["head"])
        body = [self._parse_pred(b) for b in obj.get("body", [])]
        return HornClause(
            id=obj["id"],
            name=obj["name"],
            head=head,
            body=body,
            category=obj.get("category", ""),
        )

    def _parse_pred(self, s: str) -> Pred:
        """解析 'divides(a,b)' 或 'contradiction'"""
        s = s.strip()
        m = re.match(r'(\w+)\((.+)\)', s)
        if not m:
            return make_pred(s)
        name = m.group(1)
        args_str = m.group(2)
        args = []
        depth = 0
        cur = ""
        for ch in args_str:
            if ch == '(':
                depth += 1; cur += ch
            elif ch == ')':
                depth -= 1; cur += ch
            elif ch == ',' and depth == 0:
                args.append(cur.strip()); cur = ""
            else:
                cur += ch
        if cur.strip():
            args.append(cur.strip())
        return make_pred(name, *[self._parse_term(a) for a in args])

    def _parse_term(self, t: str):
        t = t.strip()
        m = re.match(r'(\w+)\((.+)\)', t)
        if m:
            inner = []
            depth = 0; cur = ""
            for ch in m.group(2):
                if ch == '(':
                    depth += 1; cur += ch
                elif ch == ')':
                    depth -= 1; cur += ch
                elif ch == ',' and depth == 0:
                    inner.append(cur.strip()); cur = ""
                else:
                    cur += ch
            if cur.strip():
                inner.append(cur.strip())
            return make_const(m.group(1), *[self._parse_term(a) for a in inner])
        if t.isdigit():
            return make_const(t)
        if re.match(r'^[a-zA-Z]$', t):
            return make_var(t)
        return make_const(t)

    # ---------- 存储 ----------
    def add(self, clause: HornClause):
        self.clauses.append(clause)
        self.by_id[clause.id] = clause
        self.by_predicate[clause.head.name].append(clause.id)
        for b in clause.body:
            self.by_predicate[b.name].append(clause.id)
        self.by_category[clause.category].append(clause.id)

    # ---------- 检索 ----------
    def retrieve(self, goal: Pred, top_k: int = 20) -> List[HornClause]:
        """
        给定目标，返回 top-K 相关定理。
        打分：
          +10 目标谓词 == head 谓词
          +5  目标常量出现在 head
          +3  body 里含目标谓词
          +2  body 含目标常量
        """
        goal_pred = goal.name
        goal_consts = self._extract_consts(goal)

        scores: Dict[str, float] = defaultdict(float)

        # 1. head 谓词匹配
        for cid in self.by_predicate.get(goal_pred, []):
            scores[cid] += 3

        # 2. 详细打分
        for c in self.clauses:
            s = 0.0
            if c.head.name == goal_pred:
                s += 10.0
                # 常量匹配
                head_consts = self._extract_consts(c.head)
                s += 5.0 * len(goal_consts & head_consts)
            for b in c.body:
                if b.name == goal_pred:
                    s += 3.0
                    body_consts = self._extract_consts(b)
                    s += 2.0 * len(goal_consts & body_consts)
            if s > 0:
                scores[c.id] += s

        # 3. 排序
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        result_ids = [cid for cid, _ in ranked[:top_k]]
        return [self.by_id[cid] for cid in result_ids]

    def _extract_consts(self, pred: Pred) -> Set[str]:
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

    # ---------- 导出 ----------
    def to_dict(self, clause: HornClause) -> Dict:
        return {
            "id": clause.id,
            "name": clause.name,
            "category": clause.category,
            "head": str(clause.head),
            "body": [str(b) for b in clause.body],
        }

    def stats(self):
        return {
            "总数": len(self.clauses),
            "按类别": {k: len(v) for k, v in self.by_category.items()},
            "谓词数": len(self.by_predicate),
        }