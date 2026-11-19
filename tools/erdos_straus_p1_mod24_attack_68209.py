# tools/erdos_straus_p1_mod24_attack_68209.py
from tools.erdos_straus_p1_mod24_symbolic import branch_succeeds

p = 68209

# 尝试 c=8
for c in [8]:
    for r in [3, 7, 11, 23, 31, 43, 47, 59, 67, 71, 79, 83]:
        if branch_succeeds(p, r, c=c):
            print(f"c={c}, r={r}: 成功")
            break
    else:
        print(f"c={c}: 所有 r 失败")

# 尝试更大的 r
for r in [103, 107, 127, 131, 139, 151, 163, 167, 179, 191, 199, 211]:
    if branch_succeeds(p, r, c=4):
        print(f"c=4, r={r}: 成功")
        break
else:
    print("c=4, 所有大 r 失败")