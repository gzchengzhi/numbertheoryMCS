# tools/erdos_straus_p1_mod24_d_p_construct.py
"""验证 d=p 和 d=(p+r)/4 构造的覆盖率。"""
from sympy import isprime
from tools.erdos_straus_p1_mod24_symbolic import compute_g_K_N, branch_succeeds

def check_construct(p_max=100000):
    fail_p = []
    for p in range(25, p_max + 1, 24):
        if not isprime(p):
            continue
            
        found = False
        # 尝试 r 满足 p ≡ -1 (mod r) 或 p ≡ -4 (mod r)
        # 即 r 是 p+1 或 p+4 的因子
        for n in [p + 1, p + 4]:
            for r in range(3, p, 4):
                if not isprime(r):
                    continue
                if n % r == 0:
                    # 找到了满足条件的 r
                    g, K, N = compute_g_K_N(p, r, c=4)
                    # 验证我们的断言：d=p 或 d=(p+r)/4 是否真的成功
                    if n == p + 4:
                        d = p
                        target = (-N) % r
                        if d % r == target and branch_succeeds(p, r, c=4):
                            found = True
                            break
                    elif n == p + 1:
                        d = (p + r) // 4
                        target = (-N) % r
                        if d % r == target and branch_succeeds(p, r, c=4):
                            found = True
                            break
            if found:
                break
                
        if not found:
            fail_p.append(p)
            
    print(f"在 p <= {p_max} 中，有 {len(fail_p)} 个 p 无法用 d=p 或 d=(p+r)/4 构造覆盖。")
    if fail_p:
        print(f"前 10 个失败的 p: {fail_p[:10]}")

if __name__ == "__main__":
    check_construct()