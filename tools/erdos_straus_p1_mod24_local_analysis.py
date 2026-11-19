# tools/erdos_straus_p1_mod24_local_analysis.py
"""分析固定 r 下，p mod r 的成功/失败类。"""
from sympy import isprime
from tools.erdos_straus_p1_mod24_symbolic import branch_succeeds

def analyze_r(r, p_max=100000):
    success_classes = set()
    fail_classes = set()
    for p in range(25, p_max + 1, 24):
        if not isprime(p):
            continue
        a = p % r
        if a == 0:
            continue
        if branch_succeeds(p, r, c=4):
            success_classes.add(a)
        else:
            fail_classes.add(a)
    return sorted(success_classes), sorted(fail_classes)

for r in [19, 31, 43, 79, 107]:
    succ, fail = analyze_r(r)
    print(f"r={r}: 成功类 {succ}, 失败类 {fail}")