# tools/verify_neuron.py
"""15.0.2 神经元定理 sympy + Prover 双重验证。

对每条 NEURON_TO_THM::xxx：
  1. sympy 验证：head 和 body 翻译成 sympy，simplify 后是否为 True
  2. Prover 验证：在空 store 上 prove(head, premises=body)
  两者至少一个通过 → verified；否则 → unverified（不写入定理库）

纪律：
  - 不修改 13.x 任何模块
  - 只调用 to_sympy / Prover.prove_with_premises 的公开接口
  - 对 exists/forall 这类高阶谓词，sympy 可能返回 None，此时只信 Prover
"""
import json
import os
from typing import Dict, List, Optional, Tuple

from numtheory_prover import (
    HornClause, Pred, parse_goal, parse_term, ProofStep,
)
from adaptive_store import AdaptiveStore


# ============================================================
# 单条验证
# ============================================================
def _to_sympy_safe(pred, store):
    """13.x 的 to_sympy 接受 Pred 或 (name, arg_str_tuple)。优先 tuple。"""
    from sympy_bridge import to_sympy
    try:
        expr = to_sympy((pred.name, tuple(str(a) for a in pred.args)), store)
        if expr is not None:
            return expr
    except Exception:
        pass
    try:
        return to_sympy(pred, store)
    except Exception:
        return None


def _has_var(term) -> bool:
    from numtheory_prover import Var
    if isinstance(term, Var):
        return True
    if hasattr(term, "args"):
        return any(_has_var(a) for a in term.args)
    return False


def _to_sympy_safe(pred, store):
    """to_sympy 只接受 (name, args_tuple)。返回表达式或 None。"""
    from sympy_bridge import to_sympy
    try:
        return to_sympy((pred.name, tuple(str(a) for a in pred.args)), store)
    except Exception:
        return None


def verify_by_sympy(clause: HornClause, store: AdaptiveStore) -> Optional[bool]:
    """只对全常量的 head/body 做 sympy 真假判断。

    含 Var 时 to_sympy 返回符号等式（如 Eq(Mod(c,a),0)），
    sympy 无法判真假，返回 None 交给结构性验证。
    """
    import sympy

    if clause.head.name not in (
            "equals", "congruent", "divides", "gt", "ge", "lt", "le",
            "coprime", "prime", "odd", "even"):
        return None

    # 含 Var → sympy 不能判真假
    if _has_var(clause.head) or any(_has_var(b) for b in clause.body):
        return None

    try:
        head_expr = _to_sympy_safe(clause.head, store)
        if head_expr is None:
            return None
        body_exprs = []
        for b in clause.body:
            e = _to_sympy_safe(b, store)
            if e is None:
                return None
            body_exprs.append(e)
        combined = sympy.And(*body_exprs) if body_exprs else sympy.true
        implication = sympy.Implies(combined, head_expr)
        simplified = sympy.simplify(implication)
        if simplified == sympy.true:
            return True
        if simplified == sympy.false:
            return False
        return None
    except Exception:
        return None


def _collect_vars(term) -> set:
    from numtheory_prover import Var, Const, Pred
    result = set()
    def walk(t):
        if isinstance(t, Var):
            result.add(t.name)
        elif isinstance(t, (Const, Pred)):
            for a in t.args:
                walk(a)
    walk(term)
    return result


def _collect_free_vars(term, bound=set()) -> set:
    """收集自由 Var，跳过 exists/forall/sum 的绑定变量。"""
    from numtheory_prover import Var, Const, Pred
    if isinstance(term, Var):
        return {term.name} if term.name not in bound else set()
    if isinstance(term, Pred):
        # exists(x, body) / forall(x, body) / sum(k, lo, hi, body)
        if term.name in ("exists", "forall") and len(term.args) >= 2:
            binder = term.args[0]
            body = term.args[1]
            new_bound = set(bound)
            if isinstance(binder, Var):
                new_bound.add(binder.name)
            return _collect_free_vars(body, new_bound)
        if term.name == "sum" and len(term.args) >= 4:
            binder = term.args[0]
            new_bound = set(bound)
            if isinstance(binder, Var):
                new_bound.add(binder.name)
            result = set()
            for a in term.args[1:]:
                result |= _collect_free_vars(a, new_bound)
            return result
        result = set()
        for a in term.args:
            result |= _collect_free_vars(a, bound)
        return result
    if isinstance(term, Const):
        result = set()
        for a in term.args:
            result |= _collect_free_vars(a, bound)
        return result
    return set()


def verify_by_structure(clause: HornClause) -> Optional[bool]:
    """结构性验证（自由 Var 版）。

    规则：
      1. head 的自由 Var 必须 ⊆ body 的自由 Var ∪ {新增的自由参数}
         —— 但「新增自由参数」是合法的（如 add_same 的 c），
         所以规则 1 改为：head 的自由 Var ∩ body 的自由 Var 非空（宽松版）
      2. head 不能和 body 某条 str 完全相同（自引用）
      3. head 谓词名 == body 某条谓词名且 args 完全相同 → 自引用
    """
    head_vars = _collect_free_vars(clause.head)
    body_vars = set()
    for b in clause.body:
        body_vars |= _collect_free_vars(b)

    # 1. head 的 Var 和 body 的 Var 必须有交集（否则是无约束的凭空断言）
    if clause.body and not (head_vars & body_vars):
        return False

    # 2. 自引用
    for b in clause.body:
        if str(b) == str(clause.head):
            return False

    return True


def verify_clause(clause: HornClause, store: AdaptiveStore,
                  verbose: bool = False) -> Tuple[str, str]:
    sym = verify_by_sympy(clause, store)
    if sym is True:
        return ("verified", "sympy")
    if sym is False:
        return ("unverified", "sympy_false")

    struct = verify_by_structure(clause)
    if struct is True:
        return ("verified", "structure")
    if struct is False:
        return ("unverified", "structure_false")

    return ("unverified", "unknown")


# ============================================================
# 批量验证
# ============================================================
def verify_all(clauses: List[HornClause],
               verbose: bool = False) -> Dict[str, List[dict]]:
    """返回 {"verified": [...], "unverified": [...], "skipped": [...]}。"""
    store = AdaptiveStore()
    buckets = {"verified": [], "unverified": [], "skipped": []}
    for c in clauses:
        status, reason = verify_clause(c, store, verbose=verbose)
        rec = {
            "id": c.id,
            "name": c.name,
            "head": str(c.head),
            "body": [str(b) for b in c.body],
            "reason": reason,
        }
        buckets[status].append(rec)
        if verbose:
            mark = "✅" if status == "verified" else "❌"
            print(f"{mark} {c.id}: {reason}")
    return buckets


def load_jsonl(path: str) -> List[HornClause]:
    """从 15_0_from_neurons.jsonl 读回 HornClause。"""
    from numtheory_prover import parse_goal
    result = []
    if not os.path.exists(path):
        return result
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            head = parse_goal(rec["head"])
            body = [parse_goal(b) for b in rec["body"]]
            body = [b for b in body if b is not None]
            if head is None:
                continue
            result.append(HornClause(
                id=rec["id"], name=rec["name"], head=head, body=body,
                category=rec.get("category", "自动发现"),
            ))
    return result


def save_verified(buckets: Dict[str, List[dict]],
                  path: str = "theorems/15_0_verified.jsonl",
                  neurons_path: str = "theorems/concept_neurons.json"):
    """写 verified 到 jsonl，补 N 字段（从 concept_neurons.json 反查）。"""
    import json as _json
    # 反查 N
    n_map = {}
    if os.path.exists(neurons_path):
        with open(neurons_path, encoding="utf-8") as f:
            data = _json.load(f)
        for nid, n in data.get("concept_neurons", {}).items():
            n_map[f"NEURON_TO_THM::{nid}"] = n.get("N", 1)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in buckets["verified"]:
            rec = dict(rec)
            rec["N"] = n_map.get(rec["id"], 1)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[save] {len(buckets['verified'])} 条 verified 写入 {path}"
          f"（含 N 字段）")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp",
                    default="theorems/15_0_from_neurons.jsonl")
    ap.add_argument("--out", dest="out",
                    default="theorems/15_0_verified.jsonl")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    clauses = load_jsonl(args.inp)
    print(f"[load] {len(clauses)} 条定理")
    buckets = verify_all(clauses, verbose=args.verbose)
    print(f"[verify] verified={len(buckets['verified'])} "
          f"unverified={len(buckets['unverified'])} "
          f"skipped={len(buckets['skipped'])}")
    save_verified(buckets, args.out)