# guarded_prover.py
"""16.0.2 语义约束 Prover：T004 类全局恒真定理只在精确匹配时保留。

根因：T004: divides(1, a)，goal: divides(b, a)，
unify 返回 {b: 1}，语义上错误。
修法：goal 不是 divides(1, _) 时，从 store.clauses 和 self.db 临时剔除 T004，
      让 retrieve_adaptive 和 candidates 都不含 T004。
"""
from numtheory_prover import Prover, Const

class GuardedProver(Prover):
    BANNED_GLOBALS = {"T004", "T005"}   # 全局恒真，只在精确匹配时保留

    def _prove_recursive(self, goal, subst, depth, path, strategy="direct",
                         extra_db=None, energy=10.0, strict_prem=True):
        banned = set()
        # T004: divides(1, a) → 只在 goal = divides(1, _) 时保留
        if not (goal.name == "divides" and len(goal.args) == 2
                and isinstance(goal.args[0], Const)
                and goal.args[0].name == "1"):
            banned.add("T004")
        # T005: divides(a, 0) → 只在 goal = divides(_, 0) 时保留
        if not (goal.name == "divides" and len(goal.args) == 2
                and isinstance(goal.args[1], Const)
                and goal.args[1].name == "0"):
            banned.add("T005")

        if not banned:
            return super()._prove_recursive(
                goal, subst, depth, path, strategy,
                extra_db, energy, strict_prem)

        saved_db = self.db
        saved_store_clauses = None
        if self.store is not None:
            saved_store_clauses = self.store.clauses
            self.store.clauses = [c for c in self.store.clauses
                                  if c.id not in banned]
            self.db = self.store.clauses
        else:
            self.db = [c for c in self.db if c.id not in banned]
        try:
            return super()._prove_recursive(
                goal, subst, depth, path, strategy,
                extra_db, energy, strict_prem)
        finally:
            if saved_store_clauses is not None:
                self.store.clauses = saved_store_clauses
            self.db = saved_db