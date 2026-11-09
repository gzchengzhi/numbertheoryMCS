"""14.0.5e: 深度题测试的共用 fixture。不碰 131 的 rp fixture。"""
import json, os, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from adaptive_store import AdaptiveStore
from tools.deep_recursive_prover import DeepRecursiveProver
from tools.discover_from_neurons import discover_from_neurons

import numtheory_prover
numtheory_prover.ENABLE_SUBST_CONSISTENCY = True
numtheory_prover.ENABLE_EMPTY_LOWER = True


def load_deep_cases():
    path = os.path.join(ROOT, "tests", "bench", "deep", "cases.jsonl")
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _make_deep_store(max_depth=8, only_predicates=None):
    s = AdaptiveStore()
    import glob
    for f in sorted(glob.glob("theorems/*.jsonl")):
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
    from concept_domain import DomainRegistry
    DomainRegistry("domains").load_all_into(s)
    cands = discover_from_neurons(s.concept_neurons, max_depth=max_depth,
                                  only_predicates=only_predicates)
    for c in cands:
        s.concept_neurons[c["neuron_id"]] = c
    return s


@pytest.fixture
def deep_rp():
    s = _make_deep_store(max_depth=8)
    return DeepRecursiveProver(
        s, iso_edges_path=os.path.join(ROOT, "data", "iso_edges.json"))


@pytest.fixture
def deep_cases():
    return load_deep_cases()


def get_case(cases, cid):
    return next(c for c in cases if c["id"] == cid)