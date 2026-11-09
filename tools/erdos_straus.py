# tools/erdos_straus.py
"""19.0.2 Erdős–Straus 条件归约的机械验证（外围，不碰内部）。

数学基础（定理 19.0.2）：
  EP（Erdős–Straus 前提）：对素数 p ≤ 10^17，存在正整数 a,b,c 使
      4/p = 1/a + 1/b + 1/c
  （引用 Salez 2014 验证 p ≤ 10^17；Mihnea & Dumitru 2025 推到 10^18。
   系统不重复跑 10^17，只引用文献结论。）

  定理：在 EP 下，对任意素数 p ≤ 10^17 和任意 k ≥ 1，
      4/(p·k) = 1/(a·k) + 1/(b·k) + 1/(c·k)
  证明：两边乘 1/k，分配。x=ak,y=bk,z=ck 是正整数。

系统能做的（三层）：
  Layer 1：EP 实例验证（给定 (p,a,b,c)，sympy 验证 4/p = 1/a+1/b+1/c）
  Layer 2：归约恒等式验证（若 EP 实例成立，则 4/(pk) = 1/(ak)+1/(bk)+1/(ck)）
  Layer 3：n ≡ 0 (mod 4) 特例（4/(4k) = 1/(2k)+1/(3k)+1/(6k)，复用 19.0.1）

系统不能做的：
  - 不声称 EP 为真（引用文献）
  - 不自动生成 4/p 的 (a,b,c)（人手给已知解）
  - 不证明完整 Erdős–Straus 猜想

纪律：
  - 不 import deep_recursive_prover / recursive_prover / adaptive_store 的私有方法
  - 只用 sympy + numtheory_prover 的公开 parse_goal
"""
import sympy
from typing import Tuple, List, Optional

# ============================================================
# 常量
# ============================================================
EP_PRIME_BOUND = 10**17       # EP 条件范围（文档记录，程序不跑到）
SYSTEM_PRIME_BOUND = 100      # 系统实际验证的 p 上限（Layer 2 笛卡尔积）
SYSTEM_K_BOUND = 10           # Layer 2 的 k 上限


# ============================================================
# Layer 1：EP 实例验证
# ============================================================
def verify_ep_instance(p: int, a: int, b: int, c: int) -> bool:
    """给定 (p,a,b,c)，验证 4/p = 1/a + 1/b + 1/c。

    不声称"对所有 p ≤ 10^17 成立"，只验证这一个实例。
    """
    try:
        lhs = sympy.Rational(4, p)
        rhs = (sympy.Rational(1, a)
               + sympy.Rational(1, b)
               + sympy.Rational(1, c))
        return sympy.simplify(lhs - rhs) == 0
    except (ZeroDivisionError, TypeError):
        return False


# ============================================================
# Layer 2：归约恒等式验证
# ============================================================
def verify_reduction_identity(p: int, a: int, b: int, c: int, k: int) -> bool:
    """若 4/p = 1/a+1/b+1/c，则 4/(pk) = 1/(ak)+1/(bk)+1/(ck)。

    这是纯代数恒等式（P ⟹ Q 的 Q），不需要 EP 前提。
    但为了"P ⟹ Q"完整，测试里先 verify_ep_instance 再调这个。
    """
    if p <= 0 or k <= 0 or a <= 0 or b <= 0 or c <= 0:
        return False
    try:
        lhs = sympy.Rational(4, p * k)
        rhs = (sympy.Rational(1, a * k)
               + sympy.Rational(1, b * k)
               + sympy.Rational(1, c * k))
        return sympy.simplify(lhs - rhs) == 0
    except (ZeroDivisionError, TypeError):
        return False


def verify_reduction_from_ep(
        p: int, a: int, b: int, c: int, k: int,
) -> Tuple[bool, str]:
    """Layer 2 完整：先验证 EP 实例，再验证归约。

    返回 (ok, reason)。ok=True 表示"P 成立且 Q 成立"。
    """
    if not verify_ep_instance(p, a, b, c):
        return False, f"EP 实例不成立: 4/{p} != 1/{a}+1/{b}+1/{c}"
    if not verify_reduction_identity(p, a, b, c, k):
        return False, f"归约恒等式不成立: p={p},k={k}"
    return True, f"p={p},k={k}: x={a*k},y={b*k},z={c*k}"


# ============================================================
# Layer 3：n ≡ 0 (mod 4) 特例
# ============================================================
def verify_mod4_zero(k: int) -> bool:
    """4/(4k) = 1/(2k) + 1/(3k) + 1/(6k)。

    这是 1/k = 1/(2k)+1/(3k)+1/(6k) 的直接应用（1/2+1/3+1/6=1），
    不依赖 EP，对任意 k ≥ 1 成立。
    """
    if k <= 0:
        return False
    try:
        lhs = sympy.Rational(4, 4 * k)
        rhs = (sympy.Rational(1, 2 * k)
               + sympy.Rational(1, 3 * k)
               + sympy.Rational(1, 6 * k))
        return sympy.simplify(lhs - rhs) == 0
    except (ZeroDivisionError, TypeError):
        return False


# ============================================================
# 已知 EP 实例（人手给，作为测试样例，不声称穷举）
# ============================================================
# 每项 (p, a, b, c)：4/p = 1/a + 1/b + 1/c
# 这些是小的已知解，测试用。系统不声称"找到了所有 p 的解"。
KNOWN_EP_INSTANCES: List[Tuple[int, int, int, int]] = [
    (3, 1, 4, 12),     # 4/3 = 1/1 + 1/4 + 1/12 = (12+3+1)/12 = 16/12 = 4/3 ✓
    (5, 2, 4, 20),     # 4/5 = 1/2 + 1/4 + 1/20 = (10+5+1)/20 = 16/20 = 4/5 ✓
    (7, 2, 15, 210),     # 4/7 = 1/2 + 1/15 + 1/210 ✓
    (11, 3, 34, 1122),   # 4/11 = 1/3 + 1/34 + 1/1122 ✓
]


def get_valid_known_instances() -> List[Tuple[int, int, int, int]]:
    """过滤 KNOWN_EP_INSTANCES，只留 sympy 验证通过的。

    防止人手给的样例有错（如 (7,2,14,14) 可能不成立），
    系统过滤后只用真正成立的。
    """
    return [inst for inst in KNOWN_EP_INSTANCES
            if verify_ep_instance(*inst)]