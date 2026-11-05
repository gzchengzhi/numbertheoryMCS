def test_pattern_to_pred():
    """pattern 转 Pred。"""
    from tools.diagnose import _pattern_to_pred
    pat = ["divides", ["a", "b"]]
    p = _pattern_to_pred(pat, None)
    assert p is not None
    assert p.name == "divides"
    assert len(p.args) == 2
    assert type(p.args[0]).__name__ == "Var"
    assert type(p.args[1]).__name__ == "Var"


def test_pattern_to_pred_const():
    """数字转 Const。"""
    from tools.diagnose import _pattern_to_pred
    pat = ["divides", ["2", "6"]]
    p = _pattern_to_pred(pat, None)
    assert p is not None
    assert type(p.args[0]).__name__ == "Const"
    assert p.args[0].name == "2"


def test_is_comparison_only_true():
    """body 全是 gt/ge/lt/le → True。"""
    from tools.diagnose import _is_comparison_only
    from numtheory_prover import Pred, Var, Const
    body = [Pred("gt", (Var("a"), Const("0"))),
            Pred("lt", (Var("b"), Const("10")))]
    assert _is_comparison_only(body) is True


def test_is_comparison_only_false():
    """body 含 equals → False。"""
    from tools.diagnose import _is_comparison_only
    from numtheory_prover import Pred, Var
    body = [Pred("equals", (Var("a"), Var("b")))]
    assert _is_comparison_only(body) is False

def test_diagnose_auto_learn(tmp_path):
    """空 store + --auto-learn → 自动合入 + 重试成功。"""
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
                  make_rp_fn=_empty_rp, auto_learn=True)
    assert rc == 0  # 合入后重试成功