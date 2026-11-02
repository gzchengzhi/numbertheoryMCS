# D:/BookCode/numbertheoryMCS/probe.py
from dataclasses import dataclass, field
from time import perf_counter

class SearchBudgetExceeded(Exception):
    pass

@dataclass
class SearchProbe:
    strategy: str = ""
    fell_back: bool = False
    nodes_visited: int = 0
    max_depth: int = 0
    elapsed_ms: float = 0.0
    success: bool = False
    reason: str = ""
    _t0: float = field(default=0.0, repr=False)

    def start(self, strategy):
        self.strategy = strategy
        self._t0 = perf_counter()

    def visit(self, depth):
        self.nodes_visited += 1
        self.max_depth = max(self.max_depth, depth)

    def finish(self, success, fell_back, reason=""):
        self.elapsed_ms = (perf_counter() - self._t0) * 1000
        self.success, self.fell_back, self.reason = success, fell_back, reason
        return self

class NoopProbe(SearchProbe):
    def visit(self, depth): pass
    def finish(self, success, fell_back, reason=""): return self

if __name__ == "__main__":
    p = SearchProbe()
    p.start("selftest")
    for d in range(3):
        p.visit(d)
    p.finish(success=True, fell_back=False)
    assert p.nodes_visited == 3 and p.max_depth == 2
    print(f"probe self-test OK: nodes={p.nodes_visited}, depth={p.max_depth}, "
          f"elapsed={p.elapsed_ms:.2f}ms")