# tools/erdos_straus_p1_mod24_prime_q_obstruction.py
"""反例寻找：当 (p+r)/4 为素数时，是否必然失败？"""
from sympy import isprime
from tools.erdos_straus_p1_mod24_symbolic import branch_succeeds

def check_prime_q_obstruction(p_max=100000):
    count_total = 0
    count_obstructed = 0
    
    for p in range(25, p_max + 1, 24):
        if not isprime(p):
            continue
            
        # 找出所有 r < p, r ≡ 3 mod 4，使得 (p+r)/4 是素数
        obstructed_r = []
        for r in range(3, p, 4):
            if not isprime(r):
                continue
            q = (p + r) // 4
            if isprime(q):
                count_total += 1
                if not branch_succeeds(p, r, c=4):
                    obstructed_r.append(r)
                    
        # 如果对所有满足条件的 r，分支都失败，说明 p 避开了所有“素数 q”分支
        if obstructed_r:
            count_obstructed += 1
            if count_obstructed <= 10: # 打印前 10 个
                print(f"p={p}: 在素数 q 分支上全部失败，受阻的 r = {obstructed_r[:10]}...")
                
    print(f"\n在 p <= {p_max} 中，发现 {count_obstructed} 个素数 p 避开了所有的素数 q 分支。")

if __name__ == "__main__":
    check_prime_q_obstruction()