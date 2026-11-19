# tools/erdos_straus_p1_mod24_extend_r.py
"""20.1: 扩展 R 到素数 r = 31, 43, 47，计算乘积。"""
from tools.erdos_straus_p1_mod24_symbolic import compute_failure_set
from tools.erdos_straus_p1_mod24_density import failure_rate, density_upper_bound
from sympy import isprime


def extend_r_analysis():
    r_list = [3, 7, 11, 23, 31, 43, 47, 59, 67, 71, 79, 83]
    # 检查所有 r 都是素数（不调参，只做事实检查）
    for r in r_list:
        assert isprime(r), f"r={r} 不是素数，不能加入 F_r"
    
    print("=== 20.1 扩展 R 分析 ===\n")
    print(f"{'r':>4} | {'|F_r|':>6} | {'r-1':>4} | {'失败率':>8} | {'累积乘积':>12}")
    print("-" * 50)
    product = 1.0
    for r in r_list:
        F = compute_failure_set(r)
        rate = failure_rate(r)
        product *= rate
        print(f"{r:>4} | {len(F):>6} | {r-1:>4} | {rate:>8.4f} | {product:>12.6f}")
    print(f"\n最终乘积 = {product:.6f}")
    return product


if __name__ == "__main__":
    extend_r_analysis()