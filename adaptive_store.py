"""
自适应定理库：全互联网络 + 概念多边形 + 谓词槽边 + 独立依赖记录 + 链式建边

原则：
- 学习一次：三角形/链的边权在发现时一次写定
- 检索一次：只读 cooccur_edges + 计算分数 + 全排序
- 不反复查库：检索时不重跑 discover_*
- 不截断：返回全排序（top_k=None）
"""

import json
import os
import math
from collections import defaultdict
from typing import List, Dict, Set, Optional, Tuple

from numtheory_prover import HornClause, Pred, Const, Var
from theorem_store import TheoremStore


WEIGHT_FILE = "theorem_weights.json"
DEP_FILE = "dependency_records.json"

EPSILON = 0.01
MIN_WEIGHT = EPSILON
MAX_WEIGHT = 2.0
ALPHA = 0.1
BETA = 0.05
DECAY_BASE = 0.5
SLOT_SEP = "@"

MIN_DEP_COUNT = 3


def slot_id(pred_name: str, pos) -> str:
    return f"{pred_name}{SLOT_SEP}{pos}"


def is_slot(tid: str) -> bool:
    return SLOT_SEP in tid


def _sig_of_term(t) -> str:
    tn = type(t).__name__
    if tn == 'Var':
        return 'V'
    if tn == 'Const':
        if not t.args:
            return f'C:{t.name}'
        return f'F:{t.name}(' + ','.join(_sig_of_term(a) for a in t.args) + ')'
    if tn == 'Pred':
        return f'P:{t.name}(' + ','.join(_sig_of_term(a) for a in t.args) + ')'
    return '?'


def _clause_signature(clause) -> tuple:
    def pred_sig(p):
        return (p.name, tuple(_sig_of_term(a) for a in p.args))
    return (
        pred_sig(clause.head),
        tuple(pred_sig(b) for b in clause.body),
    )

# ========== 10.0 新增：head 解析 ==========

def parse_head(head_str):
    """解析字符串形式的 head，如 'divides(a, c)' -> ('divides', ('a', 'c'))"""
    if "(" not in head_str:
        return (head_str.strip(), ())
    pred, rest = head_str.split("(", 1)
    rest = rest.rstrip(")")
    return (pred.strip(), tuple(split_args(rest)))

def split_args(s):
    """按逗号分割，忽略括号内的逗号"""
    args, depth, cur = [], 0, ""
    for ch in s:
        if ch == "," and depth == 0:
            args.append(cur.strip())
            cur = ""
        else:
            if ch in "([":
                depth += 1
            elif ch in ")]":
                depth -= 1
            cur += ch
    if cur.strip():
        args.append(cur.strip())
    return args

def _parse_clause_obj(clause):
    """从 HornClause 对象提取 (pred_name, terms) 用于分类"""
    if clause is None or not hasattr(clause, 'head'):
        return ("", ())
    head = clause.head
    return (head.name, tuple(getattr(a, 'name', str(a)) for a in head.args))



class AdaptiveStore(TheoremStore):

    def __init__(self):
        self.cooccur_edges: Dict[Tuple[str, str], float] = {}
        self.edge_depth: Dict[Tuple[str, str], int] = {}
        self._aliases: Dict[str, str] = {}
        self._signature_index: Dict[tuple, str] = {}
        self._current_chain_ids: Set[str] = set()
        self._learned_ids: Set[str] = set()
        self.dependency_records: Dict[tuple, Dict[frozenset, int]] = defaultdict(
            lambda: defaultdict(int))
        super().__init__()
        self.theorem_weights: Dict[str, float] = {}
        self.usage_stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"used": 0, "success": 0, "fail": 0})
        self._virtual_theorems = []
        self._sympy_decl_cache = None
        self._ensure_all_decls()
        self.concept_neurons: Dict[str, Dict] = {}
        self.neuron_edges: Dict[Tuple[str, str], float] = {}
        self._neurons_built = False
        
        # ========== 10.0 新增：type 附加 + 虚拟定理 ==========
        
    # ============================================================
    # 10.0 概念神经元层
    # ============================================================
    def add_triangle(self, triangle: Dict, source_clause_id: str):
        """
        把一个三角形加进神经元网络。
        triangle: extract_triangles 返回的 triangles 列表中的一项
        source_clause_id: 这个三角形来自哪条定理（用于追溯）
        """
        nid = triangle['neuron']
        if nid not in self.concept_neurons:
            self.concept_neurons[nid] = {
                'neuron_id': nid,
                'type': triangle['type'],
                'lower': triangle['lower'],
                'mediator': triangle.get('mediator'),
                'anchor': triangle.get('anchor'),
                'head_pattern': triangle.get('head_pattern'),  # ← 新增
                'N': triangle['N'],
                'weight': triangle['weight'],
                'instances': [],
            }
        # 记录实例
        self.concept_neurons[nid]['instances'].append({
            'source_clause': source_clause_id,
            'lower': triangle['lower'],
            'mediator': triangle.get('mediator'),
            'anchor': triangle.get('anchor'),
            'N': triangle['N'],
        })
        # 记录边（神经元 → 神经元，如果 lower 里有神经元）
        for low in triangle['lower']:
            if isinstance(low, str) and low.startswith('NEURON::'):
                key = (low, nid)
                self.neuron_edges[key] = max(
                    self.neuron_edges.get(key, 0.0),
                    triangle['weight'],
                )

    def build_neurons_from_theorems(self, extract_fn):
        """
        从定理库批量构建神经元层。
        extract_fn: callable(clause, to_sympy, store) -> extract_triangles 的结果
        """
        from sympy_bridge import to_sympy
        for c in self.clauses:
            if getattr(c, 'type', None) != 'logic':
                continue
            r = extract_fn(c, to_sympy, self)
            for tri in r['triangles']:
                self.add_triangle(tri, c.id)
        self._neurons_built = True

    def activate_neuron(self, body_patterns: List[str],
                        neuron_type: Optional[str] = None
                        ) -> List[Tuple[str, float, str, int]]:
        """
        给定一组 body 谓词名，看能否激活某个神经元。
        返回: [(neuron_id, weight, type, N), ...]
              先按 weight 降序，再按 N 升序（N 小的优先）
        """
        activated = []
        for nid, n in self.concept_neurons.items():
            if neuron_type and n['type'] != neuron_type:
                continue
            lowers = n.get('lower', [])
            if len(lowers) != len(body_patterns):
                continue
            low_preds = []
            for low in lowers:
                if isinstance(low, tuple):
                    low_preds.append(low[0])
                elif isinstance(low, str) and low.startswith('NEURON::'):
                    low_preds.append(low)
            if sorted(low_preds) == sorted(body_patterns):
                activated.append((nid, n['weight'], n['type'], n['N']))
        activated.sort(key=lambda x: (-x[1], x[3]))
        return activated
    
    def save_neurons(self, path: str = "theorems/concept_neurons.json"):
        import json
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {
            'concept_neurons': dict(self.concept_neurons),
            'neuron_edges': {
                f"{a}|{b}": w for (a, b), w in self.neuron_edges.items()
            },
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_neurons(self, path: str = "theorems/concept_neurons.json"):
        import json
        if not os.path.exists(path):
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return
        self.concept_neurons = data.get('concept_neurons', {})
        self.neuron_edges = {}
        for key, w in data.get('neuron_edges', {}).items():
            parts = key.split("|")
            if len(parts) == 2:
                self.neuron_edges[(parts[0], parts[1])] = w
        self._neurons_built = True

    def _classify(self, head_name, body_names):
        from sympy_decls import SYMPY_DECLS
        sympy_preds = set(SYMPY_DECLS.keys())
        body_preds = set(body_names)

        if not body_preds:
            if head_name in sympy_preds:
                return "compute"
            return "fact"

        return "logic"

    def _enrich_theorem(self, clause):
        """只附加 type 属性，幂等。"""
        if hasattr(clause, 'type') and clause.type:
            return
        pred_name = clause.head.name
        body_names = []
        for b in clause.body:
            if hasattr(b, 'name'):
                body_names.append(b.name)
            else:
                body_names.append(str(b))
        clause.type = self._classify(pred_name, body_names)

    def _ensure_all_decls(self):
        """为 SYMPY_DECLS 里所有谓词构造虚拟定理。"""
        from sympy_decls import SYMPY_DECLS
        self._virtual_theorems = []
        for pred, decl in SYMPY_DECLS.items():
            self._virtual_theorems.append({
                "id": f"T_SYMPY_DECL_{pred}",
                "predicate": pred,
                "sympy": decl,
                "_virtual": True,
            })

    def find_sympy_decls(self, predicate):
        """从虚拟定理里查 sympy 声明。"""
        if self._sympy_decl_cache is None:
            self._sympy_decl_cache = {}
            for thm in self._virtual_theorems:
                decl = thm.get("sympy")
                if decl:
                    pred = decl.get("predicate")
                    self._sympy_decl_cache.setdefault(pred, []).append(decl)
        return self._sympy_decl_cache.get(predicate, [])

    # ============================================================
    # 全互联 + 结构去重
    # ============================================================
    def add(self, clause: HornClause):
        cid = clause.id
        sig = _clause_signature(clause)

        if sig in self._signature_index:
            canonical_id = self._signature_index[sig]
            self._aliases[cid] = canonical_id
            w_new = self.theorem_weights.get(cid, EPSILON)
            w_old = self.theorem_weights.get(canonical_id, EPSILON)
            self.theorem_weights[canonical_id] = max(w_old, w_new)
            self.theorem_weights.pop(cid, None)
            return
        


        self._signature_index[sig] = cid
        super().add(clause)
        self._signature_index[sig] = cid
        super().add(clause)
        self._enrich_theorem(clause)   # 10.0 新增：附加 type

        if cid.startswith("PREM_"):
            self.theorem_weights[cid] = 1.0
        else:
            if cid not in self.theorem_weights:
                self.theorem_weights[cid] = EPSILON

        for other in self.clauses:
            oid = other.id
            if oid == cid:
                continue
            key = (cid, oid) if cid < oid else (oid, cid)
            if key not in self.cooccur_edges:
                self.cooccur_edges[key] = EPSILON
                
    def mark_learned(self, ids: List[str]):
        """标记本次学习加入的定理，用于检索加成"""
        self._learned_ids = set(ids)
        
        # 10.0 新增：处理新定理自带的 sympy 声明
        updated = False
        for tid in ids:
            clause = self.by_id.get(tid)
            if clause and hasattr(clause, 'sympy_decl') and clause.sympy_decl:
                pred = clause.sympy_decl.get("predicate")
                self._virtual_theorems = [
                    v for v in self._virtual_theorems
                    if v.get("predicate") != pred
                ]
                self._virtual_theorems.append({
                    "id": f"T_SYMPY_DECL_{pred}_learned",
                    "predicate": pred,
                    "sympy": clause.sympy_decl,
                    "_virtual": True,
                })
                updated = True
        
        if updated:
            self._sympy_decl_cache = None

    def ensure_slot(self, name: str):
        if name not in self.theorem_weights:
            self.theorem_weights[name] = EPSILON
        for other in self.clauses:
            key = (name, other.id) if name < other.id else (other.id, name)
            if key not in self.cooccur_edges:
                self.cooccur_edges[key] = EPSILON

    # ============================================================
    # 参数结构相似度
    # ============================================================
    def _term_similarity(self, t1, t2) -> float:
        tn1 = type(t1).__name__
        tn2 = type(t2).__name__
        if tn1 != tn2:
            return 0.1
        if tn1 == 'Var':
            return 1.0 if t1.name == t2.name else 0.5
        if tn1 == 'Const':
            if t1.name != t2.name:
                return 0.0
            if len(t1.args) != len(t2.args):
                return 0.3
            if not t1.args:
                return 1.0
            return sum(self._term_similarity(a, b)
                       for a, b in zip(t1.args, t2.args)) / len(t1.args)
        return 0.0

    def _term_similarity_loose(self, t1, t2) -> float:
        """宽松版：Var 可以匹配任何东西"""
        tn1 = type(t1).__name__
        tn2 = type(t2).__name__

        if tn1 == 'Var' or tn2 == 'Var':
            if tn1 == tn2 == 'Var':
                return 1.0 if t1.name == t2.name else 0.7
            return 0.8

        if tn1 != tn2:
            return 0.1

        if tn1 == 'Const':
            if t1.name != t2.name:
                return 0.0
            if len(t1.args) != len(t2.args):
                return 0.3
            if not t1.args:
                return 1.0
            return sum(self._term_similarity_loose(a, b)
                       for a, b in zip(t1.args, t2.args)) / len(t1.args)
        return 0.0

    def _head_arg_similarity(self, head: Pred, goal: Pred) -> float:
        if len(head.args) != len(goal.args):
            return 0.0
        if not head.args:
            return 1.0
        return sum(self._term_similarity(h, g)
                   for h, g in zip(head.args, goal.args)) / len(head.args)

    def _loose_arg_similarity(self, head: Pred, goal: Pred) -> float:
        if len(head.args) != len(goal.args):
            return 0.0
        if not head.args:
            return 1.0
        return sum(self._term_similarity_loose(h, g)
                   for h, g in zip(head.args, goal.args)) / len(head.args)

    def _is_too_generic(self, head: Pred) -> bool:
        if not head.args:
            return False
        for a in head.args:
            if type(a).__name__ == 'Var':
                continue
            return False
        return True
    
    def _variable_consistency(self, head, goal, subst) -> float:
        """
        检查 head 里"重复出现的 Var"在 unify 后是否绑到同一表达式。
        返回：一致性得分（可正可负）
        """
        from collections import defaultdict
    
        var_positions = defaultdict(list)
    
        def walk(t, path):
            tn = type(t).__name__
            if tn == 'Var':
                var_positions[t.name].append(tuple(path))
            elif tn in ('Const', 'Pred'):
                for i, a in enumerate(t.args):
                    walk(a, path + [i])
    
        walk(head, [])
    
        score = 0.0
        for var_name, positions in var_positions.items():
            if len(positions) < 2:
                continue
            # 这个 Var 在 head 里出现多次
            goal_terms = []
            for pos in positions:
                t = goal
                ok = True
                for i in pos:
                    if hasattr(t, 'args') and i < len(t.args):
                        t = t.args[i]
                    else:
                        ok = False
                        break
                if ok:
                    goal_terms.append(t)
            if len(goal_terms) >= 2:
                first = goal_terms[0]
                if all(g == first for g in goal_terms):
                    score += 1.0
                else:
                    score -= 1.0
    
        return score

    # ============================================================
    # 打分
    # ============================================================
    def _score_all(self, goal: Pred) -> Dict[str, float]:
        """
        ★ 二值打分：head 谓词名匹配 goal 的 → 1.0，其余 → 0（不进候选）。
        排序完全由连接权重（cooccur_edges + theorem_weights + 链加成）决定。
        """
        goal_pred = goal.name
        scores: Dict[str, float] = {}
        for c in self.clauses:
            if c.head.name == goal_pred:
                scores[c.id] = 1.0
        return scores

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

    # ============================================================
    # 概念多边形发现（同谓词 / premises 匹配）
    # ============================================================
    def discover_polygons(self, goal: Pred,
                          premises: List[HornClause]) -> int:
        from numtheory_prover import unify

        goal_pred_name = goal.name
        prem_heads = [(p.id, p.head) for p in premises]
        found = 0

        for c in self.clauses:
            if c.id.startswith("PREM_"):
                continue
            if c.head.name != goal_pred_name:
                continue

            if len(c.body) == 1 and c.body[0].name == c.head.name:
                if self._match_single_body(c, prem_heads):
                    tid = c.id
                    head_slot = slot_id(c.head.name, "head")
                    body_slot = slot_id(c.body[0].name, "body0")
                    self.ensure_slot(head_slot)
                    self.ensure_slot(body_slot)
                    self._set_edge_with_depth(head_slot, body_slot, depth=1)
                    self._set_edge_with_depth(head_slot, tid, depth=3)
                    self._set_edge_with_depth(body_slot, tid, depth=3)
                    found += 1
                continue

            if len(c.body) < 2:
                continue

            matched = self._match_body_to_premises(c.body, prem_heads)
            if matched is None:
                continue

            tid = c.id
            for i in range(len(matched)):
                for j in range(i + 1, len(matched)):
                    self._set_edge_with_depth(matched[i], matched[j], depth=1)
            for slot_name, pid in matched:
                self.ensure_slot(slot_name)
                self._set_edge_with_depth(slot_name, tid, depth=2)

            found += 1
        return found

    def _match_single_body(self, clause, prem_heads):
        from numtheory_prover import unify
        for pid, phead in prem_heads:
            if unify(phead, clause.body[0], {}) is not None:
                return pid
        return None

    def _match_body_to_premises(self, body, prem_heads):
        from numtheory_prover import unify

        def _is_simple_symbol(t):
            tn = type(t).__name__
            if tn == 'Var':
                return True
            if tn == 'Const':
                return len(t.args) == 0
            return False

        def shared_positions(p1, p2):
            result = []
            for i, a1 in enumerate(p1.args):
                if not _is_simple_symbol(a1):
                    continue
                for j, a2 in enumerate(p2.args):
                    if not _is_simple_symbol(a2):
                        continue
                    if a1 == a2:
                        result.append((i, j))
            return tuple(sorted(result))

        used = set()
        matched = []
        for pos, b in enumerate(body):
            hit = None
            for i, (pid, head) in enumerate(prem_heads):
                if i in used:
                    continue
                if unify(head, b, {}) is not None:
                    hit = (i, pid, head)
                    break
            if hit is None:
                return None
            i, pid, head = hit
            used.add(i)
            matched.append((slot_id(head.name, pos), pid, b))

        head_map = {pid: head for pid, head in prem_heads}
        n = len(matched)
        for i in range(n):
            for j in range(i + 1, n):
                _, pid_i, b_i = matched[i]
                _, pid_j, b_j = matched[j]
                prem_shared = shared_positions(head_map[pid_i], head_map[pid_j])
                body_shared = shared_positions(b_i, b_j)
                if len(prem_shared) != len(body_shared):
                    return None
                if tuple(p for p, _ in prem_shared) != tuple(p for p, _ in body_shared):
                    return None
                if tuple(q for _, q in prem_shared) != tuple(q for _, q in body_shared):
                    return None

        return [(s, pid) for s, pid, _ in matched]

    def _set_edge_with_depth(self, a: str, b: str, depth: int):
        key = (a, b) if a < b else (b, a)
        if key in self.edge_depth:
            return
        w = max(EPSILON, DECAY_BASE ** (depth - 1))
        self.cooccur_edges[key] = w
        self.edge_depth[key] = depth

    # ============================================================
    # ★ 链式建边（跨谓词、跨定理）
    # ============================================================
    def discover_chains(self, goal: Pred) -> int:
        """
        从 goal 出发，找"完整依赖链"，把链上的"两两"边一次写定。
        同时把链上所有定理 id 收集到 self._current_chain_ids。
        返回发现的链数量。
        """
        found = 0
        self._current_chain_ids = set()   # ★ 重置
        for c in self.clauses:
            #if self._is_too_generic(c.head): continue
            if c.id.startswith("PREM_"):
                continue
            if c.head.name != goal.name:
                continue
            if not c.body:
                continue
            chain = self._expand_chain(c, goal, visited=frozenset(), depth=0)
            if chain is None:
                continue
            self._current_chain_ids |= chain   # ★ 收集
            chain_list = sorted(chain)
            for i in range(len(chain_list)):
                for j in range(i + 1, len(chain_list)):
                    self._set_edge_with_depth(
                        chain_list[i], chain_list[j], depth=2)
            depth_bonus = 1.0 + 0.2 * len(chain)
            self.theorem_weights[c.id] = min(
                MAX_WEIGHT,
                max(self.theorem_weights.get(c.id, EPSILON), depth_bonus)
            )
            found += 1
        return found
    
    def _expand_chain(self, clause, goal_instance, visited: frozenset,
                      depth: int = 0) -> Optional[Set[str]]:
        from numtheory_prover import unify, substitute
    
        if depth > 10:
            return None
        if clause.id in visited:
            return None
        new_visited = visited | {clause.id}
    
        # ★ 用 goal_instance 和 clause.head 做 unify，得到具体 subst
        clause_renamed = self._rename_for_chain(clause, depth)
        subst = unify(clause_renamed.head, goal_instance, {})
        if subst is None:
            return None
    
        chain = {clause.id}
    
        for b in clause_renamed.body:
            # ★ 代入 subst，得到具体子目标
            b_concrete = substitute(b, subst)
            if type(b_concrete).__name__ != 'Pred':
                return None
    
            candidates = []
            for other in self.clauses:
                #if self._is_too_generic(other.head): continue
                if other.id == clause.id:
                    continue
                if other.id in new_visited:
                    continue
                if other.id.startswith("PREM_"):
                    continue
                if other.head.name != b_concrete.name:
                    continue
                other_renamed = self._rename_for_chain(other, depth + 1)
                sub = unify(other_renamed.head, b_concrete, {})
                if sub is None:
                    continue
                sim = self._head_arg_similarity(other.head, b_concrete)
                # ★ 变量重复一致性
                consistency = self._variable_consistency(
                    other_renamed.head, b_concrete, sub)
                # ★ 综合分数
                total = sim + 0.5 * consistency
                candidates.append((total, other, b_concrete))

            if not candidates:
                return None

            candidates.sort(key=lambda x: -x[0])

            success = False
            for _, cand, sub_goal in candidates:
                if not cand.body:
                    if self._is_too_generic(cand.head):
                        continue
                    chain.add(cand.id)
                    success = True
                    break
                else:
                    sub_chain = self._expand_chain(
                        cand, sub_goal, new_visited, depth + 1)
                    if sub_chain is not None:
                        chain |= sub_chain
                        success = True
                        break

            if not success:
                return None
    
        return chain
    
    def _rename_for_chain(self, clause, depth: int) -> HornClause:
        """为链发现做重命名：每次调用生成唯一的变量前缀"""
        counter = [0]
        var_map = {}
    
        def rename_term(t):
            tn = type(t).__name__
            if tn == 'Var':
                if t.name not in var_map:
                    var_map[t.name] = Var(f"__c{depth}_{counter[0]}")
                    counter[0] += 1
                return var_map[t.name]
            if tn == 'Const':
                return Const(t.name, tuple(rename_term(a) for a in t.args))
            if tn == 'Pred':
                return Pred(t.name, tuple(rename_term(a) for a in t.args))
            return t
    
        def rename_pred(p):
            return Pred(p.name, tuple(rename_term(a) for a in p.args))
    
        return HornClause(
            id=clause.id,
            name=clause.name,
            head=rename_pred(clause.head),
            body=[rename_pred(b) for b in clause.body],
            category=clause.category,
        )

    # ============================================================
    # 持久化
    # ============================================================
    def load_weights(self, path: str = WEIGHT_FILE):
        if not os.path.exists(path):
            return
        try:
            if os.path.getsize(path) == 0:
                return
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        for tid, w in data.get("weights", {}).items():
            self.theorem_weights[tid] = w
        for tid, s in data.get("stats", {}).items():
            self.usage_stats[tid] = s
        for key, w in data.get("cooccur_edges", {}).items():
            parts = key.split("|")
            if len(parts) == 2:
                self.cooccur_edges[(parts[0], parts[1])] = w
        for key, d in data.get("edge_depth", {}).items():
            parts = key.split("|")
            if len(parts) == 2:
                self.edge_depth[(parts[0], parts[1])] = d

        self._aliases = dict(data.get("aliases", {}))
        for alias_id, canonical_id in self._aliases.items():
            if alias_id in self.theorem_weights:
                w = self.theorem_weights.pop(alias_id)
                self.theorem_weights[canonical_id] = max(
                    self.theorem_weights.get(canonical_id, EPSILON), w
                )

    def save_weights(self, path: str = WEIGHT_FILE):
        edges = {f"{a}|{b}": w for (a, b), w in self.cooccur_edges.items()
                 if abs(w - EPSILON) > 1e-6}
        depths = {f"{a}|{b}": d for (a, b), d in self.edge_depth.items()}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                "weights": dict(self.theorem_weights),
                "stats": {k: dict(v) for k, v in self.usage_stats.items()},
                "cooccur_edges": edges,
                "edge_depth": depths,
                "aliases": dict(self._aliases),
            }, f, ensure_ascii=False, indent=2)

    def load_dependency_records(self, path: str = DEP_FILE):
        if not os.path.exists(path):
            return
        try:
            if os.path.getsize(path) == 0:
                return
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return
        for key, dep_dict in data.items():
            name, arity = key.rsplit(SLOT_SEP, 1)
            for dep_str, count in dep_dict.items():
                dep_set = frozenset(dep_str.split(",")) if dep_str else frozenset()
                self.dependency_records[(name, int(arity))][dep_set] = count

    def save_dependency_records(self, path: str = DEP_FILE):
        serializable = {}
        for (name, arity), dep_dict in self.dependency_records.items():
            key = f"{name}{SLOT_SEP}{arity}"
            sub = {}
            for dep_set, count in dep_dict.items():
                if count < MIN_DEP_COUNT:
                    continue
                dep_key = ",".join(sorted(dep_set)) if dep_set else ""
                sub[dep_key] = count
            if sub:
                serializable[key] = sub
        if not serializable:
            return
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2)

    # ============================================================
    # 权值更新
    # ============================================================
    def strengthen(self, theorem_ids: List[str]):
        for tid in theorem_ids:
            w = self.theorem_weights.get(tid, EPSILON)
            self.theorem_weights[tid] = min(MAX_WEIGHT, w + ALPHA)
            self.usage_stats[tid]["used"] += 1
            self.usage_stats[tid]["success"] += 1

    def weaken(self, theorem_ids: List[str]):
        for tid in theorem_ids:
            w = self.theorem_weights.get(tid, EPSILON)
            self.theorem_weights[tid] = max(MIN_WEIGHT, w - BETA)
            self.usage_stats[tid]["used"] += 1
            self.usage_stats[tid]["fail"] += 1

    def record_dependency(self, goal: Pred, used_clauses: List[HornClause]):
        key = (goal.name, len(goal.args))
        dep_ids = []
        for c in used_clauses:
            cid = c.id
            if cid.startswith("PREM_"):
                continue
            if cid in ("COMPUTED", "SYM_INEQ"):
                continue
            dep_ids.append(cid)
        if not dep_ids:
            return
        dep_set = frozenset(dep_ids)
        self.dependency_records[key][dep_set] += 1

    # ============================================================
    # 检索（★ 全排序，不截断；不重跑 discover_*）
    # ============================================================
    def retrieve_adaptive(self, goal: Pred, top_k: Optional[int] = None,
                          expand_round: int = 0,
                          excluded_ids: Set[str] = None
                          ) -> List[HornClause]:
        if excluded_ids is None:
            excluded_ids = set()

        scores = self._score_all(goal)
        for cid in list(scores.keys()):
            w = self.theorem_weights.get(cid, EPSILON)
            scores[cid] *= (0.8 + 0.2 * min(w, 2.0))

        # 扩展只做一次（如果 expand_round > 0）
        if expand_round > 0:
            new_preds = set()
            for cid in list(scores.keys()):
                c = self.by_id.get(cid)
                if c is None:
                    continue
                for b in c.body:
                    new_preds.add(b.name)
            for pred_name in new_preds:
                for cid in self.by_predicate.get(pred_name, []):
                    if cid not in scores and cid not in excluded_ids:
                        scores[cid] = 0.5 * self.theorem_weights.get(cid, EPSILON)
                    elif cid in scores:
                        scores[cid] += 0.5

        current_ids = list(scores.keys())
        goal_slots = [slot_id(goal.name, i) for i in range(3)]
        goal_slots.append(slot_id(goal.name, "head"))

        for cid in current_ids:
            for neighbor_id, w in self.get_cooccur_neighbors(
                    cid, threshold=EPSILON * 2.0):
                if neighbor_id in excluded_ids or is_slot(neighbor_id):
                    continue
                # ★ 只加成已在 scores 里的，不新加入
                if neighbor_id in scores:
                    scores[neighbor_id] += 2.0 * w

        for s in goal_slots:
            if s not in self.theorem_weights:
                continue
            for neighbor_id, w in self.get_cooccur_neighbors(
                    s, threshold=EPSILON * 2.0):
                if neighbor_id in excluded_ids or is_slot(neighbor_id):
                    continue
                if neighbor_id not in scores:
                    scores[neighbor_id] = 4.0 * w
                else:
                    scores[neighbor_id] += 4.0 * w

        # ★ 本次学习加成：只给刚学的定理 ×100
        if self._learned_ids:
            for cid in self._learned_ids:
                if cid in scores:
                    scores[cid] *= 100.0
                else:
                    scores[cid] = 100.0

        # 依赖记录加成
        goal_key = (goal.name, len(goal.args))
        if goal_key in self.dependency_records:
            for dep_set, count in self.dependency_records[goal_key].items():
                bonus = 1.0 + 0.05 * min(count, 20)
                for cid in dep_set:
                    if cid in scores:
                        scores[cid] *= bonus

        # ★ 不重跑 discover_chains —— 链的边已经建好，通过共现边加成

        for cid in excluded_ids:
            scores.pop(cid, None)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if top_k is None:
            result_ids = [cid for cid, _ in ranked]
        else:
            result_ids = [cid for cid, _ in ranked[:top_k]]
        return [self.by_id[cid] for cid in result_ids if cid in self.by_id]

    # ============================================================
    # 共现学习
    # ============================================================
    def learn_cooccurrence(self, used_ids: List[str], alpha: float = 0.15):
        ids = [tid for tid in used_ids]
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                if a == b:
                    continue
                key = (a, b) if a < b else (b, a)
                w = self.cooccur_edges.get(key, EPSILON)
                self.cooccur_edges[key] = min(MAX_WEIGHT, w + alpha)

    def weaken_cooccurrence(self, attempted_ids: List[str], beta: float = 0.05):
        ids = [tid for tid in attempted_ids]
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                if a == b:
                    continue
                key = (a, b) if a < b else (b, a)
                w = self.cooccur_edges.get(key, EPSILON)
                self.cooccur_edges[key] = max(MIN_WEIGHT, w - beta)

    def get_cooccur_neighbors(self, tid: str, threshold: float = EPSILON * 2.0,
                              max_neighbors: Optional[int] = None
                              ) -> List[Tuple[str, float]]:
        neighbors = []
        for (a, b), w in self.cooccur_edges.items():
            if w <= threshold:
                continue
            if a == tid:
                neighbors.append((b, w))
            elif b == tid:
                neighbors.append((a, w))
        neighbors.sort(key=lambda x: x[1], reverse=True)
        if max_neighbors is None:
            return neighbors
        return neighbors[:max_neighbors]

    # ============================================================
    # 统计
    # ============================================================
    def weight_stats(self) -> Dict:
        ws = list(self.theorem_weights.values())
        edges = list(self.cooccur_edges.values())
        return {
            "平均节点权重": round(sum(ws) / max(len(ws), 1), 4),
            "最高节点权重": round(max(ws), 4) if ws else 0,
            "最低节点权重": round(min(ws), 4) if ws else 0,
            "平均边权": round(sum(edges) / max(len(edges), 1), 4),
            "最高边权": round(max(edges), 4) if edges else 0,
            "最低边权": round(min(edges), 4) if edges else 0,
            "定理数": len(self.clauses),
            "边数": len(self.cooccur_edges),
            "已初始化多边形数": len(self.edge_depth) // 3,
            "强边数(>0.5)": sum(1 for w in edges if w > 0.5),
            "依赖记录数": sum(len(d) for d in self.dependency_records.values()),
        }

    def add_lemma(self, clause, generality: float, cost: int):
        new_id = f"AUTO-{len(self.by_id):04d}"
        new_clause = HornClause(
            id=new_id, name=clause.name, head=clause.head,
            body=clause.body, category="自动引理",
        )
        self.add(new_clause)
        lemma_file = os.path.join("theorems", "auto_lemmas.jsonl")
        os.makedirs("theorems", exist_ok=True)
        record = {
            "id": new_id, "name": clause.name, "category": "自动引理",
            "head": str(clause.head), "body": [str(b) for b in clause.body],
            "generality": round(generality, 3), "cost": cost,
            "score": round(generality * (1 + math.log(max(cost, 1))), 3),
        }
        with open(lemma_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")