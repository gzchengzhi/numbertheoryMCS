def test_deep_speed():
    """USE_DEEP=1 时单题 < 0.5s。"""
    import time
    from tools.bench_competition import make_rp
    import os
    os.environ["USE_DEEP"] = "1"
    try:
        rp = make_rp()
        t0 = time.time()
        proof = rp.prove_deep("divides(a, c)",
                              ["divides(a, b)", "divides(b, c)"],
                              verbose=False)
        elapsed = time.time() - t0
        assert proof is not None
        assert elapsed < 0.5, f"单题 {elapsed:.2f}s > 0.5s"
    finally:
        os.environ.pop("USE_DEEP", None)