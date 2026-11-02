# recursive_prover.py
"""
11.0 递归点火 + 同构边（PR2.1 支持 lower_map）。

不修改 10.1 的任何模块，只调用 AdaptiveProver.prove / AdaptiveStore 的公开接口。

理论对应：
  - Cheng 2019 §8.2.4 "上层概念逐层形成"：lower 是子神经元 id 时递归
  - Cheng 2019 §8.2.4 "重合三角形"：structural 同构边迁移
  - lower_map：src 的 lower 语义 → dst 的 lower 语义的映射
  - energy 语义不变：递归点火和同构迁移都不进入 _prove_recursive
"""
from typing import Optional, List, Dict, Set, Tuple
import json
import os

from numtheory_prover import (
    parse_goal, parse_term, unify,
    Var, Const, Pred, HornClause, ProofStep,
)
from adaptive_prover import AdaptiveProver
from adaptive_store import AdaptiveStore


class RecursiveProver:
    MAX_RECURSIVE_DEPTH = 3

    def __init__(self, store: AdaptiveStore, max_depth=12,
                 max_nodes=None, max_steps=10, probe=None, verbose=False,
                 iso_edges_path: str = "data/iso_edges.json"):
        self.store = store
        self.prover = AdaptiveProver(
            store, max_depth=max_depth, max_nodes=max_nodes,
            max_steps=max_steps, probe=probe)
        self.probe = probe
        self.verbose = verbose

        self.iso_index = self._load_iso_edges(iso_edges_path)
        if verbose:
            n_edges = sum(len(v) for v in self.iso_index.values())
            print(f"[iso] loaded {n_edges} structural edges for "
                  f"{len(self.iso_index)} src neurons")

    # ============================================================
    # 公开入口
    # ============================================================
    def prove(self, goal_str: str, premises: Optional[List] = None,
              verbose: Optional[bool] = None) -> Optional[List[ProofStep]]:
        if verbose is None:
            verbose = self.verbose

        goal = parse_goal(goal_str)
        if goal is None:
            return None

        prem_preds: List[Pred] = []
        for p in (premises or []):
            if isinstance(p, str):
                pg = parse_goal(p)
                if pg is not None:
                    prem_preds.append(pg)
            elif isinstance(p, Pred):
                prem_preds.append(p)

        recursive = self._try_recursive(goal, prem_preds, _depth=0, _visited=set())
        if recursive is not None:
            if verbose:
                print(f"[recursive] 命中 {recursive['via']}")
            return recursive["proof"]

        if verbose:
            print("[recursive] 未命中，回退 10.1 prove")
        return self.prover.prove(goal_str, premises=premises, verbose=verbose)

    # ============================================================
    # PR1：递归点火
    # ============================================================
    def _try_recursive(self, goal, premises, _depth, _visited):
        
       
        if _depth > self.MAX_RECURSIVE_DEPTH:
            return None

        if self.verbose and _depth == 0:
            print(f"[trace] 进入 _try_recursive, goal={goal}, n_neurons={len(self.store.concept_neurons)}, n_premises={len(premises)}")

        for nid, neuron in self._sorted_neurons():
            if nid in _visited:
                continue
            hp = neuron.get("head_pattern")
            if hp is None:
                if self.verbose and _depth == 0:
                    print(f"[trace] skip {nid}: hp=None")
                continue

            subst = self._match_head_pattern(hp, goal)
            if self.verbose and _depth == 0 and nid.startswith("NEURON::T::divides"):
                print(f"[trace] try {nid}: hp={hp} subst={'OK' if subst is not None else 'None'}")
            
            if subst is None:
                if _depth == 0 and nid in self.iso_index:
                    migrated = self._try_iso_for_nid(
                        nid, goal, premises, _depth, _visited)
                    if migrated is not None:
                        return migrated
                continue

            lowers = neuron.get("lower", [])
            sub_steps = []
            ok = True
            for low in lowers:
                if isinstance(low, str) and low.startswith("NEURON::"):
                    sub_goal = self._neuron_head(low)
                    if sub_goal is None:
                        if self.verbose:
                            print(f"[dbg]   sub neuron {low} 无 head_pattern")
                        ok = False
                        break
                    sub = self._try_recursive(
                        sub_goal, premises, _depth + 1, _visited | {nid})
                    if sub is None:
                        if self.verbose:
                            print(f"[dbg]   sub neuron {low} 递归失败")
                        ok = False
                        break
                    sub_steps.extend(sub["proof"])
                else:
                    if not self._match_lower(low, goal, premises):
                        if self.verbose:
                            print(f"[dbg]   lower {low!r} 未匹配（图式前置不满足，正常）")
                        ok = False
                        break
            if not ok:
                continue
            
            # ★ 12.9 构造性存在：用 construct 覆盖 subst
            construct = neuron.get("construct")
            if construct:
                try:
                    from numtheory_prover import parse_term, substitute
                    for var_name, expr_str in construct.items():
                        for k in list(subst.keys()):
                            if getattr(k, "name", None) == var_name:
                                constructed = parse_term(expr_str)
                                constructed = substitute(constructed, subst)
                                subst[k] = constructed
                                if self.verbose:
                                    print(f"[construct] {nid}: {var_name} = {constructed}")
                                break
                except Exception as e:
                    if self.verbose:
                        print(f"[construct] {nid}: {e!r}")

            # ★ 13.0.5: construct 的 verify 验证
            construct = neuron.get("construct")
            if construct:
                try:
                    from numtheory_prover import parse_term, substitute, parse_goal, Pred
                    # 1. 构造 m,n
                    for var_name, expr_str in construct.items():
                        if var_name == "verify":
                            continue
                        for k in list(subst.keys()):
                            if getattr(k, "name", None) == var_name:
                                constructed = parse_term(expr_str)
                                constructed = substitute(constructed, subst)
                                subst[k] = constructed
                                break
                    # 2. 验证 verify 的 equals
                    verify = construct.get("verify", [])
                    if verify:
                        import sympy
                        from sympy_bridge import to_sympy
                        all_ok = True
                        for v_str in verify:
                            v_pred = parse_goal(v_str)
                            if v_pred is None:
                                all_ok = False
                                break
                            v_subst = substitute(v_pred, subst)
                            if v_subst.name != "equals" or len(v_subst.args) != 2:
                                all_ok = False
                                break
                            lhs = to_sympy(v_subst.args[0], self.store)
                            rhs = to_sympy(v_subst.args[1], self.store)
                            if lhs is None or rhs is None:
                                if self.verbose:
                                    print(f"[verify] {v_str}: to_sympy 失败")
                                all_ok = False
                                break
                            diff = sympy.simplify(lhs - rhs)
                            if diff != 0:
                                if self.verbose:
                                    print(f"[verify] {v_str}: diff={diff} ≠ 0")
                                all_ok = False
                                break
                            if self.verbose:
                                print(f"[verify] {v_str}: ✅")
                        if not all_ok:
                            continue
                except Exception as e:
                    if self.verbose:
                        print(f"[construct] {nid}: {e!r}")

            step = ProofStep(
                clause=HornClause(nid, f"递归点火 {nid}", goal, []),
                substitution=subst, subgoal=goal, depth=_depth,
                strategy=f"neuron:{nid}")
            return {"via": nid, "proof": [step] + sub_steps}
        return None

    # ============================================================
    # PR2：同构边加载 + 迁移
    # ============================================================
    def _load_iso_edges(self, path):
        if not os.path.exists(path):
            return {}
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
        idx = {}
        for e in data.get("edges", []):
            if e.get("kind") != "structural":
                continue
            src = e.get("src")
            if src:
                idx.setdefault(src, []).append(e)
        return idx

    def _try_iso_for_nid(self, src_nid, goal, premises, _depth, _visited):
        for edge in self.iso_index.get(src_nid, []):
            migrated = self._try_iso_migrate(
                edge, goal, premises, _depth, _visited)
            if migrated is not None:
                return migrated
        return None

    def _try_iso_migrate(self, edge, goal, premises, _depth, _visited):
        dst_nid = edge.get("dst")
        if not dst_nid or dst_nid not in self.store.concept_neurons:
            return None
        if dst_nid in _visited:
            return None

        dst_neuron = self.store.concept_neurons[dst_nid]
        dst_hp = dst_neuron.get("head_pattern")
        if dst_hp is None:
            return None

        # 1. dst head_pattern 匹配 goal
        subst = self._match_head_pattern(dst_hp, goal)
        if subst is None:
            if self.verbose:
                print(f"[dbg] iso {edge['id']}: dst {dst_nid} "
                      f"head_pattern 不匹配 goal")
            return None

        # 2. 校验
        if not self._verify_iso(edge, goal):
            if self.verbose:
                print(f"[dbg] iso {edge['id']}: verify 失败，不迁移")
            return None

        # 3. lower_map 匹配（PR2.1 核心）
        lower_map = edge.get("mapping", {}).get("lower_map")
        dst_lowers = dst_neuron.get("lower", [])
        sub_steps = []

        if lower_map:
            if len(lower_map) != len(dst_lowers):
                if self.verbose:
                    print(f"[dbg] iso {edge['id']}: lower_map 长度 {len(lower_map)} "
                          f"≠ dst lowers 长度 {len(dst_lowers)}")
                return None
            for i, lm in enumerate(lower_map):
                dst_low = lm.get("dst")
                src_low = lm.get("src")
                matched = False
                if isinstance(dst_low, (list, tuple)) and self._match_lower(dst_low, goal, premises):
                    matched = True
                elif isinstance(src_low, (list, tuple)) and self._match_lower(src_low, goal, premises):
                    matched = True
                if not matched:
                    if self.verbose:
                        print(f"[dbg] iso {edge['id']}: lower_map[{i}] "
                              f"dst={dst_low!r} src={src_low!r} 都未匹配 premises")
                    return None

                low = dst_lowers[i]
                if isinstance(low, str) and low.startswith("NEURON::"):
                    sub_goal = self._neuron_head(low)
                    if sub_goal is None:
                        return None
                    sub = self._try_recursive(
                        sub_goal, premises, _depth + 1, _visited | {dst_nid})
                    if sub is None:
                        return None
                    sub_steps.extend(sub["proof"])
        else:
            for low in dst_lowers:
                if isinstance(low, str) and low.startswith("NEURON::"):
                    sub_goal = self._neuron_head(low)
                    if sub_goal is None:
                        return None
                    sub = self._try_recursive(
                        sub_goal, premises, _depth + 1, _visited | {dst_nid})
                    if sub is None:
                        if self.verbose:
                            print(f"[dbg] iso {edge['id']}: dst {dst_nid} "
                                  f"lower {low} 递归失败")
                        return None
                    sub_steps.extend(sub["proof"])
                else:
                    if not self._match_lower(low, goal, premises):
                        if self.verbose:
                            print(f"[dbg] iso {edge['id']}: dst {dst_nid} "
                                  f"lower {low!r} 未匹配")
                        return None

        iso_id = edge["id"]
        step = ProofStep(
            clause=HornClause(
                f"ISO::{iso_id}", f"同构迁移 {iso_id}", goal, [],
                category="同构"),
            substitution=subst, subgoal=goal, depth=_depth,
            strategy=f"iso:{iso_id}")
        if self.verbose:
            print(f"[iso] 命中 {iso_id} → {dst_nid}")
        return {"via": iso_id, "proof": [step] + sub_steps}

    def _verify_iso(self, edge, goal):
        verify = edge.get("verify", {})
        method = verify.get("method")
        has_var = any(isinstance(a, Var) for a in goal.args)

        if method == "sympy_equiv":
            if has_var:
                return True
            try:
                from sympy_bridge import to_sympy
                import sympy
                expr = to_sympy(goal, self.store)
                if expr is None:
                    return False
                return bool(sympy.simplify(expr)) is True
            except Exception:
                return False

        if method == "manual_proof_ref":
            return edge.get("confidence", 0.0) >= 0.7

        return edge.get("confidence", 0.0) >= 0.7

    # ============================================================
    # 辅助
    # ============================================================
    def _sorted_neurons(self):
        def has_sub(n):
            return any(isinstance(x, str) and x.startswith("NEURON::")
                       for x in n.get("lower", []))
        items = list(self.store.concept_neurons.items())
        items.sort(key=lambda kv: (not has_sub(kv[1]), kv[0]))
        return items

    def _arg(self, a):
        if not isinstance(a, str):
            return a
        if "(" in a:
            return parse_term(a)
        # ★ 13.0.2: 纯数字字符串返回 Const，避免 Var("0") unify 失败
        if a.lstrip("-").isdigit():
            return Const(a)
        return Var(a)

    def _match_head_pattern(self, hp, goal):
        if isinstance(hp, str):
            if "(" not in hp:
                return {} if hp.strip() == goal.name else None
            name, rest = hp.split("(", 1)
            args = [a.strip() for a in rest.rstrip(")").split(",") if a.strip()]
            pred = Pred(name.strip(), tuple(self._arg(a) for a in args))
            return unify(pred, goal, {})
        if isinstance(hp, (list, tuple)) and len(hp) >= 2:
            return unify(
                Pred(hp[0], tuple(self._arg(a) for a in hp[1])), goal, {})
        return None

    def _neuron_head(self, nid):
        n = self.store.concept_neurons.get(nid)
        if not n:
            return None
        hp = n.get("head_pattern")
        if isinstance(hp, (list, tuple)) and len(hp) >= 2:
            return Pred(hp[0], tuple(self._arg(a) for a in hp[1]))
        return None

    def _match_lower(self, low, goal, premises):
        # ★ 13.0.2: lower=[] 时返回 True（C028）
        from numtheory_prover import ENABLE_EMPTY_LOWER
        if ENABLE_EMPTY_LOWER and isinstance(low, (list, tuple)) and len(low) == 0:
            return True
        
        
        if isinstance(low, (list, tuple)) and len(low) >= 2:
            pat = Pred(low[0], tuple(self._arg(a) for a in low[1]))
        elif isinstance(low, str) and "(" not in low:
            if any(p.name == low for p in premises):
                return True
            return goal.name == low
        else:
            return False
    
        if premises:
            return any(unify(pat, p, {}) is not None for p in premises)
        return unify(pat, goal, {}) is not None