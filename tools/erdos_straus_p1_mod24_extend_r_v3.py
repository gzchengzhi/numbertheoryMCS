# tools/erdos_straus_p1_mod24_extend_r_v3.py
from tools.erdos_straus_p1_mod24_symbolic import compute_failure_set
from tools.erdos_straus_p1_mod24_density import failure_rate
from tools.erdos_straus_p1_mod24_r_list import generate_r_list

r_list = generate_r_list(200)
print(f"{'r':>4} | {'|F_r|':>6} | {'r-1':>4} | {'失败率':>8} | {'累积乘积':>12}")
print("-" * 50)
product = 1.0
for r in r_list:
    F = compute_failure_set(r)
    rate = failure_rate(r)
    product *= rate
    print(f"{r:>4} | {len(F):>6} | {r-1:>4} | {rate:>8.4f} | {product:>12.6f}")
print(f"\n最终乘积 = {product:.6f}")