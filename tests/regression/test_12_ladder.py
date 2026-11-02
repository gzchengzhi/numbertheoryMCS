# tests/regression/test_12_ladder.py
import sys, os, json, glob
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from adaptive_store import AdaptiveStore
from recursive_prover import RecursiveProver
from numtheory_prover import parse_term, Var, Const

def _fixed_arg(self, a):
    if not isinstance(a, str):
        return a
    if "(" in a:
        return parse_term(a)
    if a.lstrip("-").isdigit():
        return Const(a)
    return Var(a)

RecursiveProver._arg = _fixed_arg

@pytest.fixture(scope="module")
def rp():
    store = AdaptiveStore()
    for f in sorted(glob.glob("theorems/*.jsonl")):
        store.load_jsonl(f)
    for f in sorted(glob.glob("theorems/12_0_competition/*.jsonl")):
        store.load_jsonl(f)
    with open(os.path.join(ROOT, "theorems", "concept_neurons.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    store.concept_neurons = data["concept_neurons"]
    store._neurons_built = True
    return RecursiveProver(store,
                           iso_edges_path=os.path.join(ROOT, "data", "iso_edges.json"),
                           verbose=False)

LADDER = [
    ("L1", "divides(a, c)", ["divides(a, b)", "divides(b, c)"], "neuron:"),
    ("L2", "congruent(a, c, m)", ["congruent(a, b, m)", "congruent(b, c, m)"], "neuron:"),
    ("L3", "divides(a, plus(b, c))", ["divides(a, b)", "divides(a, c)"], "neuron:"),
    ("L4", "congruent(plus(a,c), plus(b,d), m)",
           ["congruent(a, b, m)", "congruent(c, d, m)"], "neuron:"),
    ("L5", "congruent(times(a,c), times(b,d), m)",
           ["congruent(a, b, m)", "congruent(c, d, m)"], "neuron:"),
    ("L6", "congruent(power(a, p), a, p)", ["prime(p)"], "neuron:"),
    ("L7", "congruent(power(a, minus(p,1)), 1, p)",
           ["prime(p)", "coprime(a, p)"], "neuron:"),
    ("L8", "congruent(power(a, phi(m)), 1, m)",
           ["coprime(a, m)", "gt(m, 1)"], "neuron:"),
    ("L9", "congruent(power(p,2), 1, 24)", ["prime(p)", "gt(p, 3)"], "neuron:"),
]

@pytest.mark.parametrize("level,goal,premises,expect", LADDER)
def test_ladder(rp, level, goal, premises, expect):
    proof = rp.prove(goal, premises=premises, verbose=False)
    assert proof is not None, f"{level} 未证明"
    assert len(proof) >= 1
    assert any(s.strategy.startswith(expect) for s in proof), \
        f"{level} 期望 {expect} 命中，实际 strategies={[s.strategy for s in proof]}"