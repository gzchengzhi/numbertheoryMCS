def test_deep_speed_200():
    """USE_DEEP=1 200 题 < 30s。"""
    import time, os
    os.environ["USE_DEEP"] = "1"
    os.environ["SUBGOAL_SPLIT"] = "1"
    try:
        from tools.bench_competition import main
        t0 = time.time()
        main()
        elapsed = time.time() - t0
        assert elapsed < 30, f"200 题 {elapsed:.1f}s > 30s"
    finally:
        os.environ.pop("USE_DEEP", None)
        os.environ.pop("SUBGOAL_SPLIT", None)