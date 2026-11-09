"""
14.0.0 接口探针：实测 13.x 稳定 API 的每个参数。
只读，不写任何文件。跑法：
    python tools/probe_13x_api.py
"""
import os, sys, json, glob, traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

import numtheory_prover
numtheory_prover.ENABLE_SUBST_CONSISTENCY = True
numtheory_prover.ENABLE_EMPTY_LOWER = True

REPORT = []

def probe(name, fn):
    try:
        r = fn()
        REPORT.append((name, "OK", repr(r)[:300]))
        return r
    except Exception as e:
        REPORT.append((name, "EXC", f"{type(e).__name__}: {e}"))
        return None


# ---------- 1. parse_goal ----------
from numtheory_prover import parse_goal, parse_term, Pred, Var, Const, HornClause

probe("parse_goal('divides(a, c)')",
      lambda: parse_goal("divides(a, c)"))
probe("parse_goal('congruent(a, b, m)')",
      lambda: parse_goal("congruent(a, b, m)"))
probe("parse_goal('exists(m, exists(n, and(gt(m,n), coprime(m,n))))')",
      lambda: parse_goal("exists(m, exists(n, and(gt(m,n), coprime(m,n))))"))
probe("parse_goal('prime_infinite')",
      lambda: parse_goal("prime_infinite"))
probe("parse_term('divides(a, b)')",
      lambda: parse_term("divides(a, b)"))

# ---------- 2. AdaptiveStore ----------
from adaptive_store import AdaptiveStore
store = AdaptiveStore()
probe("AdaptiveStore()", lambda: "ok")

def load_store():
    for f in sorted(glob.glob("theorems/*.jsonl")):
        base = os.path.basename(f)
        if "learn_log" in base or "candidates" in base:
            continue
        store.load_jsonl(f)
    with open("theorems/concept_neurons.json", encoding="utf-8") as fh:
        store.concept_neurons = json.load(fh)["concept_neurons"]
    store._neurons_built = True
    from concept_domain import DomainRegistry
    DomainRegistry("domains").load_all_into(store)
    return len(store.clauses), len(store.concept_neurons)

probe("store load (jsonl + neurons + domains)", load_store)

probe("store.by_id 大小", lambda: len(store.by_id))
probe("store.by_predicate['divides'] 数量",
      lambda: len(store.by_predicate.get("divides", [])))
probe("store.concept_neurons 数量", lambda: len(store.concept_neurons))

# 关键：depth1 神经元是否存在
D1 = "NEURON::T::divides::@0-@1::arity=2"
probe(f"concept_neurons['{D1}'] 存在", lambda: D1 in store.concept_neurons)
probe(f"concept_neurons['{D1}'] 的 lower",
      lambda: store.concept_neurons[D1]["lower"] if D1 in store.concept_neurons else None)
probe(f"concept_neurons['{D1}'] 的 head_pattern",
      lambda: store.concept_neurons[D1]["head_pattern"] if D1 in store.concept_neurons else None)

# retrieve_adaptive
probe("store.retrieve_adaptive(divides(a,c), top_k=5)",
      lambda: [c.id for c in store.retrieve_adaptive(
          parse_goal("divides(a, c)"), top_k=5)])

# ---------- 3. RecursiveProver ----------
from recursive_prover import RecursiveProver
rp = probe("RecursiveProver(store, iso_edges_path=...)",
           lambda: RecursiveProver(store,
               iso_edges_path=os.path.join(ROOT, "data", "iso_edges.json")))

def p1():
    return rp.prove("divides(a, c)",
                    premises=["divides(a, b)", "divides(b, c)"],
                    verbose=False)
probe("rp.prove(divides(a,c), [a|b,b|c])", p1)
probe("rp.prove 返回 strategies",
      lambda: [s.strategy for s in p1()] if p1() else None)

def p2():
    return rp.prove("divides(a, c)",
                    premises=["divides(a, b)", "divides(b, c)"],
                    verbose=True)
probe("rp.prove(divides(a,c), verbose=True)",
      lambda: "ok（verbose 输出见 stdout）")
p2()

# ---------- 4. AdaptiveProver 公开入口 ----------
from adaptive_prover import AdaptiveProver
ap = probe("AdaptiveProver(store)", lambda: AdaptiveProver(store))
probe("ap.prove(divides(a,c), [a|b,b|c])",
      lambda: [s.strategy for s in ap.prove(
          "divides(a, c)",
          premises=["divides(a, b)", "divides(b, c)"],
          verbose=False) or []])

# ---------- 5. DeepRecursiveProver ----------
from tools.deep_recursive_prover import DeepRecursiveProver
from tools.discover_from_neurons import discover_from_neurons

def make_deep():
    s = AdaptiveStore()
    for f in sorted(glob.glob("theorems/*.jsonl")):
        base = os.path.basename(f)
        if "learn_log" in base or "candidates" in base:
            continue
        s.load_jsonl(f)
    with open("theorems/concept_neurons.json", encoding="utf-8") as fh:
        s.concept_neurons = json.load(fh)["concept_neurons"]
    s._neurons_built = True
    from concept_domain import DomainRegistry
    DomainRegistry("domains").load_all_into(s)
    cands = discover_from_neurons(s.concept_neurons, max_depth=8)
    for c in cands:
        s.concept_neurons[c["neuron_id"]] = c
    return s, cands

print("\n" + "=" * 80)
print("[PROBE] discover_from_neurons 产出的 id 和 lower")
print("=" * 80)
_, cands = make_deep()
for c in cands:
    print(f"  id   = {c['neuron_id']}")
    print(f"  N    = {c['N']}")
    print(f"  hp   = {c['head_pattern']}")
    print(f"  low0 = {c['lower'][0]}")
    print(f"  low1 = {c['lower'][1]}")
    print()

print("=" * 80)
print("[PROBE] depth1 神经元实际 id（主库里所有 @0-@0 / @0-@1）")
print("=" * 80)
s, _ = make_deep()
for nid in s.concept_neurons:
    if "T::divides" in nid and "depth" not in nid:
        print(f"  {nid}")
        print(f"    lower = {s.concept_neurons[nid].get('lower')}")
        print(f"    hp    = {s.concept_neurons[nid].get('head_pattern')}")
print()

print("=" * 80)
print("[PROBE] DeepRecursiveProver 4步链 实际 strategies")
print("=" * 80)
s, _ = make_deep()
drp = DeepRecursiveProver(
    s, iso_edges_path=os.path.join(ROOT, "data", "iso_edges.json"))
proof = drp.prove(
    "divides(a, e)",
    premises=["divides(a, b)", "divides(b, c)",
              "divides(c, d)", "divides(d, e)"],
    verbose=False)
if proof is None:
    print("  proof = None")
else:
    for i, st in enumerate(proof):
        print(f"  [{i}] strategy = {st.strategy}")
        print(f"       subgoal  = {st.subgoal}")
        print(f"       depth    = {st.depth}")
        print(f"       subst    = {st.substitution}")
print()

print("=" * 80)
print("[PROBE] DeepRecursiveProver 4步链 verbose（[deep] 输出）")
print("=" * 80)
s, _ = make_deep()
drp = DeepRecursiveProver(
    s, iso_edges_path=os.path.join(ROOT, "data", "iso_edges.json"))
drp.prove(
    "divides(a, e)",
    premises=["divides(a, b)", "divides(b, c)",
              "divides(c, d)", "divides(d, e)"],
    verbose=True)

# ---------- 输出报告 ----------
print("\n" + "=" * 80)
print("13.x 稳定 API 接口探针报告")
print("=" * 80)
for name, status, detail in REPORT:
    mark = "✅" if status == "OK" else "❌"
    print(f"{mark} [{status}] {name}")
    if status != "OK":
        print(f"      {detail}")
print("=" * 80)