# tools/erdos_straus_p1_mod24_crt_check.py
"""用 CRT 检查固定 R 下是否存在永久失败类。"""
from sympy.ntheory.modular import crt
from tools.erdos_straus_p1_mod24_symbolic import compute_failure_set

R = [3, 7, 11, 19, 23, 31, 43, 47, 59, 67, 71, 79, 83, 107]
F_dict = {r: compute_failure_set(r) for r in R}

# 用递归组合
def find_common_failure(rs, idx=0, current_mod=1, current_res=0):
    if idx == len(rs):
        return current_res, current_mod
    r = rs[idx]
    for a in F_dict[r]:
        # 用 CRT 合并 current_res mod current_mod 和 a mod r
        m, res = crt([current_mod, r], [current_res, a])
        if m is None:
            continue
        result = find_common_failure(rs, idx+1, m, res)
        if result is not None:
            return result
    return None

result = find_common_failure(R)
if result is None:
    print("不存在永久失败类：固定 R 覆盖所有 p")
else:
    res, mod = result
    print(f"存在永久失败类: p ≡ {res} (mod {mod})")
    print(f"该类的最小素数约为: {res}")