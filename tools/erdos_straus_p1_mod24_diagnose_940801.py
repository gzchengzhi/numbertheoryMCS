# tools/erdos_straus_p1_mod24_diagnose_940801.py
from tools.erdos_straus_p1_mod24_symbolic import branch_succeeds
from sympy import primerange

p = 940801
C = 5.71
import math
r_max = int(C * math.log(p))
print(f"p = {p}, r_max = {r_max}")
for r in primerange(3, r_max + 1):
    if r % 4 == 3:
        ok = branch_succeeds(p, r, c=4)
        print(f"r = {r:>3}: {'成功' if ok else '失败'}")