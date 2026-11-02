# tests/regression/test_defaults_unchanged.py
from adaptive_prover import AdaptiveProver
from adaptive_store import AdaptiveStore

def test_adaptive_prover_defaults():
    store = AdaptiveStore()
    ap = AdaptiveProver(store)
    assert ap.max_depth == 12
    assert ap.max_nodes is None
    assert ap.max_steps == 10
    from probe import NoopProbe
    assert isinstance(ap.probe, NoopProbe)

def test_prover_defaults():
    from numtheory_prover import Prover
    store = AdaptiveStore()
    p = Prover(store)
    assert p.max_depth == 12
    assert p.max_nodes is None
    assert p.max_steps == 10          # Prover 内部默认，未被 AdaptiveProver 透传前