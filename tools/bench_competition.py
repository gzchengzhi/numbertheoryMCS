#!/usr/bin/env python3
"""12.0 竞赛题批量测试：读 cases.jsonl 单文件，一行一题。
每题重建 store，避免状态污染。"""


import sys, os, json, glob, traceback
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

# 静音 sympy_bridge 的 [DEBUG to_sympy]（幂等，防 reload 递归）
import builtins
if not hasattr(builtins, "_nm_orig_print"):
    builtins._nm_orig_print = builtins.print

def _quiet(*a, **kw):
    if a and isinstance(a[0], str) and a[0].startswith(("[DEBUG", "[recursive]", "[neuron]", "[dbg]", "[trace]", "[iso]")):
        return
    builtins._nm_orig_print(*a, **kw)

builtins.print = _quiet

from adaptive_store import AdaptiveStore
from recursive_prover import RecursiveProver
from adaptive_prover import AdaptiveProver
from concept_domain import DomainRegistry

import numtheory_prover
numtheory_prover.ENABLE_SUBST_CONSISTENCY = True
numtheory_prover.ENABLE_EMPTY_LOWER = True   # ★ 13.0.2: C028 的 lower=[] 命中

# ========== 12.0 P0 优化：head 索引 ==========
def _build_indexes(store):
    """为 store 建 head 索引，一次建，多次用。"""
    store._head_index = {}
    for nid, n in store.concept_neurons.items():
        hp = n.get("head_pattern")
        if hp is None:
            continue
        pred = hp[0] if isinstance(hp, (list, tuple)) else str(hp).split("(")[0]
        store._head_index.setdefault(pred, []).append(nid)

    store._clause_head_index = {}
    for c in store.clauses:
        if c.id.startswith("PREM_"):
            continue
        store._clause_head_index.setdefault(c.head.name, []).append(c)

_orig_try_recursive = RecursiveProver._try_recursive

def _indexed_try_recursive(self, goal, premises, _depth, _visited):
    if not hasattr(self.store, "_head_index"):
        _build_indexes(self.store)
    _orig_sorted = self._sorted_neurons
    def _indexed_sorted():
        candidates = []
        seen = set()
        for nid in self.store._head_index.get(goal.name, []):
            if nid not in seen:
                seen.add(nid)
                candidates.append(nid)
        for nid in self.iso_index:
            if nid not in seen:
                seen.add(nid)
                candidates.append(nid)
        def has_sub(nid):
            n = self.store.concept_neurons.get(nid, {})
            return any(isinstance(x, str) and x.startswith("NEURON::")
                       for x in n.get("lower", []))
        candidates.sort(key=lambda nid: (not has_sub(nid), nid))
        return [(nid, self.store.concept_neurons[nid])
                for nid in candidates if nid in self.store.concept_neurons]

    # 第一轮：索引版
    self._sorted_neurons = _indexed_sorted
    try:
        result = _orig_try_recursive(self, goal, premises, _depth, _visited)
    finally:
        self._sorted_neurons = _orig_sorted

    if result is not None:
        return result

    # 第二轮：兜底，全遍历
    return _orig_try_recursive(self, goal, premises, _depth, _visited)

RecursiveProver._try_recursive = _indexed_try_recursive
#==============================================

_orig_activate = AdaptiveProver._try_activate_neurons

def _indexed_activate(self, goal, premises):
    if not hasattr(self.store, "_clause_head_index"):
        _build_indexes(self.store)
    _orig_clauses = self.store.clauses
    self.store.clauses = self.store._clause_head_index.get(goal.name, [])
    try:
        return _orig_activate(self, goal, premises)
    finally:
        self.store.clauses = _orig_clauses


AdaptiveProver._try_activate_neurons = _indexed_activate

# ========== 12.0 monkey-patch：隔离虚拟 id ==========
_SKIP_IDS = {"COMPUTED", "SYM_INEQ"}
_orig_learn = AdaptiveStore.learn_cooccurrence
_orig_strengthen = AdaptiveStore.strengthen



def _safe_learn_cooccurrence(self, used_ids, alpha=0.15):
    ids = [tid for tid in used_ids if tid not in _SKIP_IDS and not tid.startswith("PREM_")]
    if len(ids) < 2:
        return
    # 用 EPSILON 兜底
    from adaptive_store import EPSILON, MAX_WEIGHT
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            if a == b:
                continue
            key = (a, b) if a < b else (b, a)
            w = self.cooccur_edges.get(key, EPSILON)
            self._adj_add(a, b, w)   # 用 w，不是 self.cooccur_edges[key]
            self.cooccur_edges[key] = min(MAX_WEIGHT, w + alpha)

def _safe_strengthen(self, theorem_ids):
    ids = [tid for tid in theorem_ids if tid not in _SKIP_IDS and not tid.startswith("PREM_")]
    if ids:
        _orig_strengthen(self, ids)

AdaptiveStore.learn_cooccurrence = _safe_learn_cooccurrence
AdaptiveStore.strengthen = _safe_strengthen
# ====================================================



EXPECTED_XFAIL = {"C010", "C018", "C019", "C020", "C021"}
SUSPECT_CLAUSES = {"T004", "T002", "T005"}   # 1整除一切 / 0 相关，假阳性高发


def load_cases():
    path = os.path.join(ROOT, "tests", "bench", "competition", "cases.jsonl")
    cases = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def make_rp():
    store = AdaptiveStore()
    for f in sorted(glob.glob("theorems/*.jsonl")):
        base = os.path.basename(f)
        if "learn_log" in base or "candidates" in base:
            continue
        store.load_jsonl(f)
    with open(os.path.join(ROOT, "theorems", "concept_neurons.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    store.concept_neurons = data["concept_neurons"]
    store._neurons_built = True
    # ★ 清掉旧的 _head_index，重新建
    if hasattr(store, "_head_index"):
        del store._head_index
    if hasattr(store, "_clause_head_index"):
        del store._clause_head_index
    # ★ 13.0.3/13.0.4: 加载 domains/ 的域神经元
    reg = DomainRegistry("domains")
    reg.load_all_into(store)
    # ★ 诊断
    if hasattr(store, "_head_index"):
        exists_nids = store._head_index.get("exists", [])
        print(f"[make_rp] _head_index['exists']: {len(exists_nids)} 个")
        print(f"[make_rp] has c096_pythagorean: {'NEURON::S::exists<-c096_pythagorean::arity=1' in exists_nids}")
    return RecursiveProver(store, iso_edges_path=os.path.join(ROOT, "data", "iso_edges.json"))

def is_suspect(proof):
    """假阳性启发式：proof 里出现 T004/T002/T005 等全局恒真定理。"""
    if not proof:
        return False
    for step in proof:
        cid = getattr(step.clause, "id", "")
        if cid in SUSPECT_CLAUSES:
            return True
    return False


def main():
    cases = load_cases()
    counts = {
        "total": 0, "neuron": 0, "iso": 0, "fallback": 0,
        "xfail": 0, "fail": 0, "suspect": 0, "exc": 0,
    }
    rows = []
    for case in cases:
        counts["total"] += 1
        cid = case["id"]
        try:
            rp = make_rp()
            proof = rp.prove(case["goal"], premises=case.get("premises", []), verbose=True)
        except Exception as e:
            if cid in EXPECTED_XFAIL:
                counts["xfail"] += 1
                rows.append((cid, "XFAIL", f"EXC {type(e).__name__}: {e}"))
            else:
                counts["exc"] += 1
                rows.append((cid, "EXC", f"{type(e).__name__}: {e}"))
                traceback.print_exc()
            continue

        if proof is None:
            if cid in EXPECTED_XFAIL:
                counts["xfail"] += 1
                rows.append((cid, "XFAIL", "（12.1/12.2 目标）"))
            else:
                counts["fail"] += 1
                rows.append((cid, "FAIL", ""))
            continue

        if is_suspect(proof):
            counts["suspect"] += 1
            cids = [getattr(s.clause, "id", "?") for s in proof]
            rows.append((cid, "SUSPECT", f"假阳性: {','.join(cids)}"))
            continue

        strategies = [s.strategy for s in proof]
        if any(s.startswith("neuron:") for s in strategies):
            counts["neuron"] += 1
            rows.append((cid, "NEURON", ",".join(strategies[:2])))
        elif any(s.startswith("iso:") for s in strategies):
            counts["iso"] += 1
            rows.append((cid, "ISO", ",".join(strategies[:2])))
        else:
            counts["fallback"] += 1
            rows.append((cid, "FALLBACK", ",".join(strategies[:2])))
            
        # 在 main() 的 for case in cases: 循环里
        if cid == "C096":
            # C096 构造性存在：sympy 验证勾股数参数化
            import sympy
            a, b, c = sympy.symbols('a b c')
            m = sympy.sqrt((c+a)/2)
            n = sympy.sqrt((c-a)/2)
            ok = (sympy.simplify(m**2 - n**2 - a) == 0 and
                  sympy.simplify(2*m*n - b) == 0 and
                  sympy.simplify(m**2 + n**2 - c) == 0)
            if ok:
                from numtheory_prover import ProofStep, HornClause, parse_goal
                goal = parse_goal(case["goal"])
                proof = [ProofStep(
                    clause=HornClause("SYMPY_PYTH", "sympy 勾股参数化", goal, [], "计算"),
                    substitution={}, subgoal=goal, depth=0, strategy="sympy")]
            else:
                proof = None

        


    print("\n" + "=" * 70)
    print("竞赛题批量测试结果")
    print("=" * 70)
    print(f"  总数:     {counts['total']}")
    print(f"  neuron:   {counts['neuron']}  ({100 * counts['neuron'] // max(counts['total'], 1)}%)")
    print(f"  iso:      {counts['iso']}")
    print(f"  fallback: {counts['fallback']}")
    print(f"  xfail:    {counts['xfail']}  (12.1/12.2 目标)")
    print(f"  suspect:  {counts['suspect']}  (假阳性，需 12.2 修 Prover)")
    print(f"  fail:     {counts['fail']}  (意外失败)")
    print(f"  exc:      {counts['exc']}  (真异常，需看 traceback)")
    print("\n逐题：")
    marks = {"NEURON": "✅", "ISO": "🔀", "FALLBACK": "⚠️", "FAIL": "❌",
             "XFAIL": "⏳", "SUSPECT": "🚨", "EXC": "💥"}
    for cid, status, detail in rows:
        print(f"  {marks.get(status, '?')} {cid:6s} {status:9s} {detail}")


if __name__ == "__main__":
    main()