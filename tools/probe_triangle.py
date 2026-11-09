"""
14.0.5e 探针：验证概念三角形递归。
只读，不改任何文件。跑法：python tools/probe_triangle.py
"""
import os
import sys
import json
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

import numtheory_prover
numtheory_prover.ENABLE_SUBST_CONSISTENCY = True
numtheory_prover.ENABLE_EMPTY_LOWER = True

from adaptive_store import AdaptiveStore
from concept_domain import DomainRegistry
from tools.deep_recursive_prover import DeepRecursiveProver
from tools.discover_from_neurons import discover_from_neurons


def build_store(max_depth=8):
    """返回 (store, candidates)。"""
    store = AdaptiveStore()
    for f in sorted(glob.glob("theorems/*.jsonl")):
        base = os.path.basename(f)
        if "learn_log" in base or "candidates" in base:
            continue
        store.load_jsonl(f)
    with open("theorems/concept_neurons.json", encoding="utf-8") as fh:
        store.concept_neurons = json.load(fh)["concept_neurons"]
    store._neurons_built = True
    DomainRegistry("domains").load_all_into(store)
    candidates = discover_from_neurons(store.concept_neurons, max_depth=max_depth)
    for c in candidates:
        store.concept_neurons[c["neuron_id"]] = c
    return store, candidates


def build_prover(store):
    return DeepRecursiveProver(
        store, iso_edges_path=os.path.join(ROOT, "data", "iso_edges.json"))


def show_proof(proof):
    if proof is None:
        print("  proof = None")
        return
    for i, st in enumerate(proof):
        print(f"  [{i}] strategy = {st.strategy}")
        print(f"       subgoal  = {st.subgoal}")
        print(f"       depth    = {st.depth}")
        print(f"       subst    = {st.substitution}")


def main():
    store, candidates = build_store(8)

    print("=" * 80)
    print("[PROBE] discover_from_neurons 产出")
    print("=" * 80)
    for c in candidates:
        print(f"  {c['neuron_id']}  N={c['N']}  w={c['weight']}")
        print(f"    hp  = {c['head_pattern']}")
        print(f"    low = {c['lower']}")
    print()

    prover = build_prover(store)

    print("=" * 80)
    print("[PROBE] depth2 单独 prove（verbose=True）")
    print("=" * 80)
    proof2 = prover.prove(
        "divides(a, c)",
        premises=["divides(a, b)", "divides(b, c)"],
        verbose=True)
    show_proof(proof2)
    print()

    print("=" * 80)
    print("[PROBE] D001 4步链")
    print("=" * 80)
    proof_d001 = prover.prove(
        "divides(a, e)",
        premises=["divides(a, b)", "divides(b, c)",
                  "divides(c, d)", "divides(d, e)"],
        verbose=False)
    show_proof(proof_d001)
    print()

    print("=" * 80)
    print("[PROBE] D004 反例（应 None）")
    print("=" * 80)
    proof_d004 = prover.prove(
        "divides(a, d)",
        premises=["divides(a, b)", "divides(b, c)", "congruent(c, d, m)"],
        verbose=False)
    show_proof(proof_d004)
    print()

    print("=" * 80)
    print("[PROBE] D005 反例（应 None）")
    print("=" * 80)
    proof_d005 = prover.prove(
        "divides(a, d)",
        premises=["divides(a, b)", "divides(c, d)"],
        verbose=False)
    show_proof(proof_d005)
    print()

    print("=" * 80)
    print("[PROBE] D002 8步链")
    print("=" * 80)
    proof_d002 = prover.prove(
        "divides(a, i)",
        premises=[f"divides({x}, {y})" for x, y in
                  zip("abcdefgh", "bcdefghi")],
        verbose=False)
    show_proof(proof_d002)
    print()


if __name__ == "__main__":
    main()