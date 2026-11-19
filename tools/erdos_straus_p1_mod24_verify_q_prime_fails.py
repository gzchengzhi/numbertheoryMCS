# tools/erdos_straus_p1_mod24_verify_q_prime_fails.py
"""验证假说：若 q=(p+r)/4 是素数，则分支必定失败。"""
from sympy import isprime
from tools.erdos_straus_p1_mod24_symbolic import branch_succeeds

def verify_hypothesis(p_max=100000):
    violations = []
    total_cases = 0
    
    for p in range(25, p_max + 1, 24):
        if not isprime(p):
            continue
            
        for r in range(3, p, 4):
            if not isprime(r):
                continue
            q = (p + r) // 4
            if isprime(q):
                total_cases += 1
                if branch_succeeds(p, r, c=4):
                    violations.append((p, r, q))
                    
    print(f"总共检查了 {total_cases} 个 q 为素数的分支。")
    if not violations:
        print("✅ 假说成立：对于所有 q 为素数的分支，分支必定失败！")
    else:
        print(f"❌ 假说不成立：发现 {len(violations)} 个反例。")
        print("前 10 个反例 (p, r, q):")
        for v in violations[:10]:
            print(f"  p={v[0]}, r={v[1]}, q={v[2]}")

if __name__ == "__main__":
    verify_hypothesis()