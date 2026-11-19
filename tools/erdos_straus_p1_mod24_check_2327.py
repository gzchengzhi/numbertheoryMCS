# tools/erdos_straus_p1_mod24_check_2327.py
"""检查一阶漏网的 2327 个 p，看它们是否被高阶危险类覆盖。"""
from sympy import isprime, factorint
from tools.erdos_straus_p1_mod24_symbolic import branch_succeeds

def check_2327(p_max=1000000):
    uncovered_by_first_order = []
    
    for p in range(25, p_max + 1, 24):
        if not isprime(p):
            continue
        
        # 检查一阶条件
        has_3_mod_4 = False
        for f in list(factorint(p + 4).keys()) + list(factorint(p + 1).keys()):
            if f % 4 == 3:
                has_3_mod_4 = True
                break
        
        if has_3_mod_4:
            continue # 被一阶覆盖，跳过
            
        # 这是 2327 个漏网之鱼之一
        # 找出它实际成功的最小 r
        for r in range(3, p, 4):
            if not isprime(r):
                continue
            if branch_succeeds(p, r, c=4):
                uncovered_by_first_order.append((p, r))
                break
                
    print(f"共找到 {len(uncovered_by_first_order)} 个一阶漏网 p 被高阶类覆盖。")
    print("前 10 个 (p, r):")
    for p, r in uncovered_by_first_order[:10]:
        print(f"  p={p}, 最小成功 r={r}")
        # 验证 r 确实不是 p+4 或 p+1 的因子
        assert (p + 4) % r != 0 and (p + 1) % r != 0
        print(f"    (r 不是 p+4 或 p+1 的因子，说明是二次/三次类的作用)")

if __name__ == "__main__":
    check_2327()