"""14.0.5e: 深度题测试的辅助函数。不 import conftest，避免相对导入问题。"""
import json, os, glob

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_deep_cases():
    path = os.path.join(ROOT, "tests", "bench", "deep", "cases.jsonl")
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def get_case(cases, cid):
    return next(c for c in cases if c["id"] == cid)


def make_deep_store(max_depth=8, only_predicates=None):
    from adaptive_store import AdaptiveStore
    from concept_domain import DomainRegistry
    from tools.discover_from_neurons import discover_from_neurons

    s = AdaptiveStore()
    for f in sorted(glob.glob(os.path.join(ROOT, "theorems", "*.jsonl"))):
        base = os.path.basename(f)
        if "learn_log" in base or "candidates" in base:
            continue
        s.load_jsonl(f)
    with open(os.path.join(ROOT, "theorems", "concept_neurons.json"), encoding="utf-8") as fh:
        s.concept_neurons = json.load(fh)["concept_neurons"]
    s._neurons_built = True
    if hasattr(s, "_head_index"):
        del s._head_index
    if hasattr(s, "_clause_head_index"):
        del s._clause_head_index
    DomainRegistry("domains").load_all_into(s)
    cands = discover_from_neurons(s.concept_neurons, max_depth=max_depth,
                                  only_predicates=only_predicates)
    for c in cands:
        s.concept_neurons[c["neuron_id"]] = c
    return s