# tools/erdos_straus_p1_mod24_algebraic_exclusion.py
"""验证代数排除条件是否严格等价于 branch_succeeds。"""
from sympy import isprime, divisors
from tools.erdos_straus_p1_mod24_symbolic import compute_g_K_N, branch_succeeds

def check_equivalent(p_max=10000):
    mismatches = []
    
    for p in range(25, p_max + 1, 24):
        if not isprime(p):
            continue
            
        for r in range(3, p, 4):
            if not isprime(r):
                continue
                
            g, K, N = compute_g_K_N(p, r, c=4)
            n2 = N * N
            target = (-N) % K
            
            # 检查真实情况
            real_success = branch_succeeds(p, r, c=4)
            
            # 检查代数条件：是否存在 d 满足同余（直接枚举 N^2 的因子）
            # 为了极简，我们只检查 N 的 9 个因子（因为我们假设 N=pq 即 q 是素数的情况）
            # 这里直接枚举 divisors，看是否与 branch_succeeds 一致
            real_d_found = any((d % K == target and (n2 // d) % K == target) for d in divisors(n2))
            
            if real_success != real_d_found:
                mismatches.append((p, r, real_success, real_d_found))
                
    if not mismatches:
        print("✅ 代数条件与 branch_succeeds 完全等价！")
    else:
        print(f"❌ 发现 {len(mismatches)} 个不匹配。")
        for m in mismatches[:10]:
            print(f"p={m[0]}, r={m[1]}, real_success={m[2]}, d_found={m[3]}")

if __name__ == "__main__":
    check_equivalent()