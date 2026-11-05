def test_diagnose_success(capsys):
    from tools.diagnose import diagnose
    rc = diagnose("divides(a, c)",
                  ["divides(a, b)", "divides(b, c)"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "✅" in out


def test_diagnose_empty_store(capsys):
    """空 store → 失败 + 候选。"""
    from adaptive_store import AdaptiveStore
    from recursive_prover import RecursiveProver
    from tools.diagnose import diagnose

    def _empty_rp():
        s = AdaptiveStore()
        import json, os
        if os.path.exists("theorems/concept_neurons.json"):
            with open("theorems/concept_neurons.json", encoding="utf-8") as fh:
                s.concept_neurons = json.load(fh)["concept_neurons"]
        return RecursiveProver(s, iso_edges_path="data/iso_edges.json")

    rc = diagnose("divides(b, a)",
                  ["equals(a, plus(times(b,q), 0))"],
                  make_rp_fn=_empty_rp)
    out = capsys.readouterr().out
    assert rc == 1
    assert "❌" in out
    assert "候选神经元" in out