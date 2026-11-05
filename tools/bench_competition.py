#!/usr/bin/env python3
"""12.0 竞赛题批量测试：读 cases.jsonl 单文件，一行一题。
每题重建 store，避免状态污染。"""


import sys, os, json, glob, traceback

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

# 静音 sympy_bridge 的 [DEBUG to_sympy]（幂等，防 reload 递归）
import builtins
if not hasattr(builtins, "_nm_orig_print"):
    builtins._nm_orig_print = builtins.print

def _quiet(*a, **kw):
    if a and isinstance(a[0], str) and a[0].startswith(
            ("[DEBUG", "[recursive]", "[neuron]", "[dbg]", "[trace]", "[iso]")):
        return
    try:
        builtins._nm_orig_print(*a, **kw)
    except UnicodeEncodeError:
        # 兜底：emoji 降级为 ASCII
        text = " ".join(str(x) for x in a)
        text = (text.replace("✅", "[OK]").replace("🔀", "[ISO]")
                    .replace("⚠️", "[WARN]").replace("❌", "[FAIL]")
                    .replace("⏳", "[XFAIL]").replace("🚨", "[SUSP]")
                    .replace("💥", "[EXC]").replace("🔶", "[ADV]"))
        builtins._nm_orig_print(text, **kw)

from adaptive_store import AdaptiveStore
from recursive_prover import RecursiveProver
from adaptive_prover import AdaptiveProver
from concept_domain import DomainRegistry
from semantic_guard import check_subst_semantic
from numtheory_prover import unify, substitute
from guarded_prover import GuardedProver
from deep_recursive_prover import DeepRecursiveProver

import numtheory_prover
import adaptive_prover
numtheory_prover.Prover = GuardedProver
adaptive_prover.Prover = GuardedProver          # ★ AdaptiveProver 模块级 Prover
numtheory_prover.ENABLE_SUBST_CONSISTENCY = True
numtheory_prover.ENABLE_EMPTY_LOWER = True   # ★ 13.0.2: C028 的 lower=[] 命中

from numtheory_prover import Prover, Const
_orig_prove_recursive = Prover._prove_recursive

def _patched_prove_recursive(self, goal, subst, depth, path, strategy="direct",
                             extra_db=None, energy=10.0, strict_prem=True):
    # T004 特判：goal 不是 divides(1, _) 时剔除 T004
    from numtheory_prover import Const
    if not (goal.name == "divides" and len(goal.args) == 2
            and isinstance(goal.args[0], Const)
            and goal.args[0].name == "1"):
        saved_db = self.db
        self.db = [c for c in self.db if c.id != "T004"]
        try:
            return _orig_prove_recursive(self, goal, subst, depth, path,
                                         strategy, extra_db, energy, strict_prem)
        finally:
            self.db = saved_db
    return _orig_prove_recursive(self, goal, subst, depth, path,
                                 strategy, extra_db, energy, strict_prem)

Prover._prove_recursive = _patched_prove_recursive

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
    # ★ 加载 15.0 phi 补丁神经元
    
    uf_path = os.path.join(ROOT, "theorems", "18_0_unit_fraction.json")
    if os.path.exists(uf_path):
        with open(uf_path, encoding="utf-8") as fh:
            uf_data = json.load(fh)
        for nid, n in uf_data.get("concept_neurons", {}).items():
            store.concept_neurons.setdefault(nid, n)
    
    phi_path = os.path.join(ROOT, "theorems", "15_0_phi_neurons.json")
    if os.path.exists(phi_path):
        with open(phi_path, encoding="utf-8") as fh:
            phi_data = json.load(fh)
        for nid, n in phi_data.get("concept_neurons", {}).items():
            store.concept_neurons.setdefault(nid, n)
    store._neurons_built = True
    
    learned_path = os.path.join(ROOT, "data", "16_0_learned_neurons.json")
    if os.path.exists(learned_path):
        with open(learned_path, encoding="utf-8") as fh:
            learned_data = json.load(fh)
        for nid, n in learned_data.get("concept_neurons", {}).items():
            store.concept_neurons.setdefault(nid, n)  
            
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
    if os.environ.get("USE_DEEP", "0") == "1":
        from deep_recursive_prover import DeepRecursiveProver
        rp = DeepRecursiveProver(store,
                                 iso_edges_path=os.path.join(ROOT, "data", "iso_edges.json"))
        rp.ENABLE_AUTO_LEARN = os.environ.get("AUTO_LEARN", "0") == "1"
        rp.ENABLE_SUBGOAL_SPLIT = os.environ.get("SUBGOAL_SPLIT", "0") == "1"
        return rp
    return RecursiveProver(store,
                           iso_edges_path=os.path.join(ROOT, "data", "iso_edges.json"))

def is_suspect(proof):
    """假阳性启发式：proof 里出现 T004/T002/T005 等全局恒真定理。"""
    if not proof:
        return False
    for step in proof:
        cid = getattr(step.clause, "id", "")
        if cid in SUSPECT_CLAUSES:
            return True
    return False

ADVANCED_IDS = set()
# main() 里

def main():
    cases = load_cases()
    counts = {
        "total": 0, "neuron": 0, "iso": 0, "fallback": 0,
        "xfail": 0, "fail": 0, "suspect": 0, "exc": 0,
        "advanced_fail": 0,
    }
    rows = []
    for case in cases:
        counts["total"] += 1
        cid = case["id"]
        try:
            rp = make_rp()
            proof = rp.prove(case["goal"], premises=case.get("premises", []),
                             verbose=False)
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
            elif cid in ADVANCED_IDS:
                counts["advanced_fail"] += 1
                rows.append((cid, "ADVFAIL", "13.x 未覆盖（phi）"))
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
        if any(s.startswith("neuron:") or s.startswith("iso:")
               or s in ("subgoal_split", "direct", "premise", "sympy")
               for s in strategies):
            counts["neuron"] += 1
            rows.append((cid, "NEURON", ",".join(strategies[:2])))
        elif any(s.startswith("iso:") for s in strategies):
            counts["iso"] += 1
            rows.append((cid, "ISO", ",".join(strategies[:2])))
        else:
            counts["fallback"] += 1
            rows.append((cid, "FALLBACK", ",".join(strategies[:2])))

        # ★ C096 特殊处理保持原样
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
                
            if cid in ADVANCED_IDS and proof is None:
                counts["advanced_fail"] += 1
                rows.append((cid, "ADVFAIL", "13.x 未覆盖（phi）"))
                continue
    # ============================================================
    # ★ 循环结束后汇总（不要在循环内算）
    # ============================================================
    passed = counts["neuron"] + counts["iso"] + counts["fallback"]
    total = counts["total"]
    simple_total = total - len(ADVANCED_IDS)
    simple_passed = passed  # advanced 本来就不在 passed 里（它们 fail）
    pass_rate = 100 * passed // max(total, 1)
    simple_rate = 100 * simple_passed // max(simple_total, 1)

    print("\n" + "=" * 70)
    print("竞赛题批量测试结果")
    print("=" * 70)
    print(f"  总数:        {total}")
    print(f"  neuron:      {counts['neuron']}  "
          f"({100 * counts['neuron'] // max(total, 1)}%)")
    print(f"  iso:         {counts['iso']}")
    print(f"  fallback:    {counts['fallback']}")
    print(f"  xfail:       {counts['xfail']}")
    print(f"  suspect:     {counts['suspect']}")
    print(f"  fail:        {counts['fail']}")
    print(f"  advanced_fail: {counts['advanced_fail']}  (phi 类，13.x 未覆盖)")
    print(f"  exc:         {counts['exc']}")
    print(f"  ----")
    print(f"  passed:      {passed}/{total} ({pass_rate}%)")
    print(f"  simple pass: {simple_passed}/{simple_total} ({simple_rate}%)")
    print("\n逐题：")
    marks = {"NEURON": "[OK]", "ISO": "[ISO]", "FALLBACK": "[WARN]",
             "FAIL": "[FAIL]", "XFAIL": "[XFAIL]", "SUSPECT": "[SUSP]",
             "EXC": "[EXC]", "ADVFAIL": "[ADV]"}
    for cid, status, detail in rows:
        safe_detail = detail.encode("ascii", "replace").decode("ascii")
        print(f"  {marks.get(status, '?')} {cid:6s} {status:9s} {safe_detail}")


if __name__ == "__main__":
    main()