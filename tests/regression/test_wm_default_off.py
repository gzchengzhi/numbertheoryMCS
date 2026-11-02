# tests/regression/test_wm_default_off.py
def test_wm_default_off():
    from adaptive_prover import AdaptiveProver
    from adaptive_store import AdaptiveStore
    from working_memory import NoopWorkingMemory
    store = AdaptiveStore()
    ap = AdaptiveProver(store)
    assert isinstance(ap.working_memory, NoopWorkingMemory)

def test_noop_wm_passes_all_candidates():
    from working_memory import NoopWorkingMemory
    wm = NoopWorkingMemory()
    cands = [("n1", 1.0, "single", 1), ("n2", 0.8, "transitive", 1)]
    assert wm.filter_candidates(cands) == cands