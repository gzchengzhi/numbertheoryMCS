# tools/erdos_straus_p1_mod24_diagnose_68209.py
from tools.erdos_straus_p1_mod24_symbolic import compute_g_K_N, branch_succeeds
from sympy import factorint

p = 68209
R_list = [3, 7, 11, 23, 31, 43, 47, 59, 67, 71, 79, 83]

print(f"p = {p}, p ≡ 1 (mod 24) = {p % 24 == 1}\n")
for r in R_list:
    g, K, N = compute_g_K_N(p, r, c=4)
    ok = branch_succeeds(p, r, c=4)
    factors = factorint(N)
    print(f"r = {r:>2}: g={g}, K={K}, N={N}")
    print(f"        N 的素因子: {factors}")
    print(f"        分支成功: {ok}\n")