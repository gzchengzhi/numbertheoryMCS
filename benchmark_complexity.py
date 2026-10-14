# benchmark_complexity.py
"""
6 道训练题：验证依赖记录的强化与独立存储
"""
import os
import time
import glob
import json
from adaptive_prover import AdaptiveProver
from adaptive_store import AdaptiveStore, EPSILON
from numtheory_prover import parse_goal


def load_store():
    from numtheory_prover import build_theorem_db
    store = AdaptiveStore()
    for c in build_theorem_db():
        store.add(c)
    for p in sorted(glob.glob('theorems/*.jsonl')):
        store.load_jsonl(p)
    store.load_weights()
    store.load_dependency_records()
    return store


def train_until_success(goal_str, premises, label="",
                        max_iters=1, verbose_every=5):
    print(f"\n{'='*70}")
    print(f"【训练】{label or goal_str}")
    print(f"{'='*70}")
    print(f"  目标: {goal_str}")
    print(f"  前提: {premises}")

    store = load_store()
    ap = AdaptiveProver(store, max_rounds=3, base_top_k=20)

    history = []
    first_success_iter = None
    t0 = time.time()

    for it in range(1, max_iters + 1):
        proof = ap.prove(goal_str, strategy="direct",
                         premises=premises, verbose=False)
        store.save_weights()
        store.save_dependency_records()

        record = {
            "iter": it,
            "success": proof is not None,
            "proof_len": len(proof) if proof else 0,
            "proof_chain": [s.clause.id for s in proof] if proof else [],
        }
        history.append(record)

        if proof and first_success_iter is None:
            first_success_iter = it

        if it == 1 or it % verbose_every == 0 or it == max_iters:
            # 打印依赖记录
            _goal = parse_goal(goal_str)
            goal_key = (_goal.name, len(_goal.args))
            deps = store.dependency_records.get(goal_key, {})
            dep_summary = {tuple(sorted(ds)): cnt for ds, cnt in deps.items()}
            print(f"  iter {it:3d}: success={record['success']}, "
                  f"dep[{goal_key}] = {dep_summary}")

    elapsed = time.time() - t0
    if first_success_iter:
        print(f"\n  ★ 首次成功: 第 {first_success_iter} 次")
        print(f"    证明链: {history[first_success_iter-1]['proof_chain']}")
    else:
        print(f"\n  ✗ {max_iters} 次内未成功")
    print(f"    耗时: {elapsed:.2f} 秒")

    return history


def main():
    print("=" * 70)
    print("6 道训练题：依赖记录强化 + 独立存储")
    print("=" * 70)

    tasks = [
        # 同余传递 - 参数组 1
        ("congruent(a, c, m)",
         ["congruent(a,b,m)", "congruent(b,c,m)"],
         "同余传递-1"),
        # 同余传递 - 参数组 2
        ("congruent(d, f, m)",
         ["congruent(d,e,m)", "congruent(e,f,m)"],
         "同余传递-2"),
        # 整除传递 - 参数组 1
        ("divides(a, c)",
         ["divides(a,b)", "divides(b,c)"],
         "整除传递-1"),
        # 整除传递 - 参数组 2
        ("divides(p, r)",
         ["divides(p,q)", "divides(q,r)"],
         "整除传递-2"),
        # 同余自反性（无前提）
        ("congruent(a, a, m)", [], "同余自反"),
        # 同余对称性（单前提）
        ("congruent(b, a, m)", ["congruent(a,b,m)"], "同余对称"),
        # 三层同余传递
        ("congruent(a, d, m)",
         ["congruent(a,b,m)", "congruent(b,c,m)", "congruent(c,d,m)"],
         "三层同余传递"),
        # 四层同余传递
        ("congruent(a, e, m)",
         ["congruent(a,b,m)", "congruent(b,c,m)",
          "congruent(c,d,m)", "congruent(d,e,m)"],
         "四层同余传递"),
    ]

    all_results = {}
    for goal, prems, label in tasks:
        hist = train_until_success(goal, prems, label=label, max_iters=1)
        all_results[label] = hist

    # 汇总
    print(f"\n{'='*70}")
    print("汇总：依赖记录文件内容")
    print(f"{'='*70}")

    dep_file = "dependency_records.json"
    if os.path.exists(dep_file):
        with open(dep_file, 'r', encoding='utf-8') as f:
            dep_data = json.load(f)
        print(json.dumps(dep_data, ensure_ascii=False, indent=2))
    else:
        print("(dependency_records.json 不存在)")

    # 保存训练历史
    with open('training_history.json', 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n训练历史已保存到 training_history.json")


if __name__ == "__main__":
    main()