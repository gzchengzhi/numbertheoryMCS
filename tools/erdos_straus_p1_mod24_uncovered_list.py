# tools/erdos_straus_p1_mod24_uncovered_list.py
"""20.2: 导出在指定 R 下仍未覆盖的素数列表。"""
import json
from sympy import isprime
from tools.erdos_straus_p1_mod24_symbolic import branch_succeeds


def find_uncovered(R_list, p_max=100000):
    """返回未覆盖的素数列表。"""
    uncovered = []
    for p in range(25, p_max + 1, 24):
        if not isprime(p):
            continue
        # 只要有一个分支成功，就算被覆盖
        covered = any(branch_succeeds(p, r, c=4) for r in R_list)
        if not covered:
            uncovered.append(p)
    return uncovered


def classify_uncovered(uncovered, R_list):
    """为每个未覆盖的 p，统计它在所有 r 上失败时的失败原因。"""
    classified = []
    for p in uncovered:
        # 在这里我们只看所有 r 都失败
        # 记录 N_r 的结构：N_r = p(p+r)/g
        from tools.erdos_straus_p1_mod24_symbolic import compute_g_K_N
        info = {"p": p, "r_failures": []}
        for r in R_list:
            g, K, N = compute_g_K_N(p, r, c=4)
            # 为了便于观察，我们可以记录 N_r 的因子数量
            from sympy import factorint
            factors = factorint(N)
            info["r_failures"].append({
                "r": r,
                "N": N,
                "num_factors": sum(factors.values()),
                "K": K
            })
        classified.append(info)
    return classified


if __name__ == "__main__":
    R_list = [3, 7, 11, 23, 31, 43, 47, 59, 67, 71, 79, 83]
    uncovered = find_uncovered(R_list)
    
    # 写文件
    output_path = "theorems/20_2_uncovered_p1_mod24.json"
    data = {
        "R_list": R_list,
        "p_max": 100000,
        "uncovered_count": len(uncovered),
        "uncovered_list": uncovered
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"未覆盖素数数量: {len(uncovered)}")
    print(f"未覆盖素数列表: {uncovered}")
    print(f"已保存到 {output_path}")