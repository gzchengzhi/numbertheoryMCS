# tools/erdos_straus_p1_mod24_timing_estimate.py
"""20.4 耗时估算：测 p_max=10^6, r ≤ 1000 的单个 p/r 耗时。"""
import time
from sympy import isprime
from tools.erdos_straus_p1_mod24_symbolic import branch_succeeds
from tools.erdos_straus_p1_mod24_r_list import generate_r_list


def estimate_timing():
    r_list = generate_r_list(1000)
    print(f"r ≤ 1000: {len(r_list)} 个素数")
    print(f"r_list 前 10: {r_list[:10]}")
    print(f"r_list 后 10: {r_list[-10:]}")
    print()

    # 测几个 p 的耗时
    test_p = [1009, 10009, 100003, 1000003, 9999991]
    for p in test_p:
        if not isprime(p):
            continue
        if p % 24 != 1:
            continue
        start = time.time()
        for r in r_list[:20]:  # 先只测前 20 个 r
            branch_succeeds(p, r, c=4)
        elapsed = time.time() - start
        print(f"p={p}: 前 20 个 r 耗时 {elapsed:.3f}s, 估算全 r_list 耗时 {elapsed * len(r_list) / 20:.2f}s")
        print(f"  估算 p_max=10^6 总耗时: {elapsed * len(r_list) / 20 * 10**6 / 24 / 1:.1f}s (粗略)")
        print()


if __name__ == "__main__":
    estimate_timing()