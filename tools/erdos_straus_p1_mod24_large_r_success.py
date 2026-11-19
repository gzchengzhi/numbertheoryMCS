# tools/erdos_straus_p1_mod24_large_r_success.py
"""检查固定的大 r 下，哪些 p 被覆盖，以及对应的 d 是什么。"""
from sympy import isprime, divisors
from tools.erdos_straus_p1_mod24_symbolic import compute_g_K_N

def find_success_p_for_large_r(r, p_max=100000):
    successes = []
    for p in range(25, p_max + 1, 24):
        if not isprime(p):
            continue
        g, K, N = compute_g_K_N(p, r, c=4)
        n2 = N * N
        target = (-N) % r
        found_d = None
        for d in divisors(n2):
            if d % r == target and (n2 // d) % r == target:
                found_d = d
                break
        if found_d is not None:
            successes.append((p, found_d, N))
    return successes

for r in [107, 167]:
    print(f"\n=== 分析大分支 r = {r} ===")
    successes = find_success_p_for_large_r(r, p_max=100000)
    print(f"在 p <= 100000 中，有 {len(successes)} 个 p 被 r={r} 覆盖。")
    for p, d, N in successes[:5]:
        print(f"  p={p}, d={d}, N={N}, N mod r={N%r}")