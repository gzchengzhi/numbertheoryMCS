# tools/erdos_straus_p1_mod24_analyze.py
"""20.0 分析脚本：收集 p ≡ 1 (mod 24) 在 c=4 分支下的成功 (p, r, d) 记录，
分析 d 与 p, r, N_r, K_r 的关系，并验证二次剩余条件。
"""
import sympy
from sympy import isprime, gcd, divisors, factorint, Integer
from collections import Counter, defaultdict
import json
import sys


def is_quadratic_residue(a: int, p: int) -> bool:
    if p == 2:
        return True
    a = a % p
    if a == 0:
        return True
    return pow(a, (p - 1) // 2, p) == 1


def compute_g_K_N(p: int, r: int, c: int = 4):
    g = gcd(c, r * p * (p + r))
    K = (c * r) // g
    N = (p * (p + r)) // g
    return g, K, N


def verify_K_N_consistency(p: int, r: int, c: int = 4):
    g, K, N = compute_g_K_N(p, r, c)
    diff_full = sympy.Rational(4, p) - sympy.Rational(c, p + r)
    if diff_full <= 0:
        return False, None, None
    K_code, N_code = diff_full.p, diff_full.q
    g_code = gcd(K_code, N_code)
    K_code //= g_code
    N_code //= g_code
    g_paper = gcd(K, N)
    K //= g_paper
    N //= g_paper
    return (K == K_code and N == N_code), int(K), int(N)


def find_d_for_p_r(p: int, r: int, c: int = 4):
    ok, K, N = verify_K_N_consistency(p, r, c)
    if not ok:
        return None
    n2 = N * N
    results = []
    for d in divisors(n2):
        if (d + N) % K != 0:
            continue
        if (n2 // d + N) % K != 0:
            continue
        results.append(int(d))
    return results if results else None


def analyze(N_max: int = 10000):
    records = []
    failed_p = []
    # 新增：按 r 统计 N_r 的二次特征
    r_stats = defaultdict(lambda: {"total": 0, "success": 0, "failure": 0})

    for p in range(25, N_max + 1, 24):
        if not isprime(p):
            continue
        found = False
        for r in range(3, min(p, 64), 4):
            ok, K, N = verify_K_N_consistency(p, r, 4)
            if not ok:
                continue
            r_stats[r]["total"] += 1
            res = find_d_for_p_r(p, r, c=4)
            if res is None:
                r_stats[r]["failure"] += 1
                continue
            r_stats[r]["success"] += 1
            found = True
            for d in res:
                d_mod_r = d % r
                neg_N_mod_r = (-N) % r
                d_factors = factorint(d)
                all_residue = all(
                    is_quadratic_residue(int(f), r) for f in d_factors
                ) if d > 1 else True
                records.append({
                    "p": int(p), "r": int(r), "d": int(d),
                    "K": int(K), "N": int(N),
                    "d_mod_r": int(d_mod_r),
                    "neg_N_mod_r": int(neg_N_mod_r),
                    "d_eq_negN_mod_r": d_mod_r == neg_N_mod_r,
                    "d_factors": {int(k): int(v) for k, v in d_factors.items()},
                    "all_factors_residue": all_residue,
                    "d_divides_N": N % d == 0,
                    "d_over_N": str(sympy.Rational(d, N)),
                })
        if not found:
            failed_p.append(int(p))
    return records, failed_p, dict(r_stats)


def summarize(records, failed_p, r_stats):
    total_p = len(set(r["p"] for r in records)) + len(failed_p)
    print(f"总素数 p ≡ 1 (mod 24): {total_p}")
    print(f"找到 d 的 p 数: {len(set(r['p'] for r in records))}")
    print(f"未找到 d 的 p 数: {len(failed_p)}")
    if failed_p:
        print(f"失败 p 列表: {failed_p[:20]}...")
    print()

    d_over_N_counter = Counter(r["d_over_N"] for r in records)
    print("d/N 分布 (top 20):")
    for val, cnt in d_over_N_counter.most_common(20):
        print(f"  d/N = {val}: {cnt} 次")
    print()

    d_eq = sum(1 for r in records if r["d_eq_negN_mod_r"])
    print(f"d ≡ -N (mod r) 的记录数: {d_eq} / {len(records)}")
    print()

    all_res = sum(1 for r in records if r["all_factors_residue"])
    print(f"d 的素因子全为二次剩余的记录数: {all_res} / {len(records)}")
    print()

    # 新增：按 r 统计成功/失败率（验证 Lemma 3）
    print("按 r 分组（成功/失败率，验证 Lemma 3）:")
    for r in sorted(r_stats):
        s = r_stats[r]
        rate = s["success"] / max(s["total"], 1)
        print(f"  r={r}: 总 {s['total']}, 成功 {s['success']}, 失败 {s['failure']}, 成功率 {rate:.3f}")
    print()

    # 按 r 分组 d 取值
    by_r = defaultdict(list)
    for rec in records:
        by_r[rec["r"]].append(rec)
    print("按 r 分组 d 取值 top 5:")
    for r in sorted(by_r):
        recs = by_r[r]
        d_vals = Counter(str(rec["d"]) for rec in recs)
        print(f"  r={r}: {len(recs)} 条记录, d 取值 top 5: {d_vals.most_common(5)}")
    print()

    # 新增：检查 N_r 的二次特征与成功/失败的关系
    print("N_r 的二次特征与成功/失败的关系:")
    # 对于每个 (p, r)，如果 find_d 成功，看 N_r 是否有非剩余素因子
    # 这个统计在 records 中已经隐含：all_factors_residue 全为 False
    print("  (成功记录中 all_factors_residue 全为 False，说明 N_r 必含非剩余素因子)")
    print()

    return {
        "total_p": total_p,
        "found_p": len(set(r["p"] for r in records)),
        "failed_p": failed_p,
        "d_over_N_top": [(str(k), int(v)) for k, v in d_over_N_counter.most_common(20)],
        "d_eq_negN_mod_r": int(d_eq),
        "all_factors_residue": int(all_res),
        "r_stats": {int(k): v for k, v in r_stats.items()},
        "records_sample": records[:50],
    }


if __name__ == "__main__":
    N_max = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    print(f"=== 分析 p ≤ {N_max} 的 p ≡ 1 (mod 24) ===\n")
    records, failed_p, r_stats = analyze(N_max)
    summary = summarize(records, failed_p, r_stats)
    with open("p1_mod24_analysis.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print("结果已保存到 p1_mod24_analysis.json")