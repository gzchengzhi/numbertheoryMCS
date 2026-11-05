# semantic_guard.py
"""16.0.1 语义约束：head 的 Const 不能绑 goal 的 Var。

T004: divides(1, a) vs divides(b, a) → unify {b: 1} → 拒绝
T005: divides(x, y) vs divides(b, a) → unify {x: b, y: a} → 允许
"""
from typing import Set


def _collect_vars(t) -> Set[str]:
    from numtheory_prover import Var, Const, Pred
    result = set()
    def walk(x):
        if isinstance(x, Var):
            result.add(x.name)
        elif isinstance(x, (Const, Pred)):
            for a in x.args:
                walk(a)
    walk(t)
    return result


def _collect_consts(t) -> Set[str]:
    from numtheory_prover import Const, Pred
    result = set()
    def walk(x):
        if isinstance(x, Const):
            if not x.args:
                result.add(x.name)
            for a in x.args:
                walk(a)
        elif isinstance(x, Pred):
            for a in x.args:
                walk(a)
    walk(t)
    return result


def check_subst_semantic(goal, head, subst) -> bool:
    """head 的 Const 不能绑 goal 的 Var。

    T004: head=divides(1, a), goal=divides(b, a), subst={b: 1}
    → head_consts={1}, goal_vars={b, a}, b∈goal_vars 且 1∈head_consts → False
    """
    if not subst:
        return True
    head_consts = _collect_consts(head)
    goal_vars = _collect_vars(goal)
    for var, val in subst.items():
        vn = getattr(var, "name", None)
        cn = getattr(val, "name", None) if hasattr(val, "name") else None
        if vn is None or cn is None:
            continue
        if vn in goal_vars and cn in head_consts:
            return False
    return True