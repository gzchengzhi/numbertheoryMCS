# tests/test_20_5_finiteness.py
"""20.5 的有限性验证：固定 p 时，成功分支等价于有限整除条件。"""
import pytest
from sympy import isprime

def test_q_minus_one_is_divisibility():
    """验证 q ≡ -1 (mod r) 等价于 r | p+4。"""
    p = 73
    r = 7
    q = (p + r) // 4  # q = 20
    assert q % r == (-1) % r
    assert (p + 4) % r == 0

def test_q_minus_quarter_is_divisibility():
    """验证 q ≡ -1/4 (mod r) 等价于 r | p+1。"""
    p = 73
    r = 5  # 注意：r=5 不是 r≡3(mod4)，这里只验证代数恒等式
    # q = (73+5)/4 = 19.5 不是整数，所以我们换一个 p 使得 p ≡ 3 (mod 4)
    # 实际上，r | p+1 时，r=5 是一个例子，但 r 必须是素数
    # 为了严谨，我们直接验证恒等式本身：
    # 若 4q ≡ p (mod r)，则 q ≡ -1/4 (mod r) => 4q ≡ -1 (mod r) => p ≡ -1 (mod r)
    assert (73 + 1) % 5 == 4  # 73 % 5 = 3, 不等于 4，所以这个具体例子不满足
    # 我们换一个正确的例子
    p = 71  # p ≡ 3 (mod 4)
    r = 5  # r ≡ 1 (mod 4) 但只验证代数
    # 实际上我们需要 r | p+1，例如 p=71, r=3 满足 r | 72
    p = 71
    r = 3
    assert (p + 1) % r == 0
    q = (p + r) // 4  # q = 18.5, 不是整数，因为 p+r = 74 不能被 4 整除
    # 为了保证 (p+r)/4 是整数，p ≡ 1 (mod 4) 且 r ≡ 3 (mod 4)
    # 所以取 p = 73, r = 7 时，q = 20，4q = 80 ≡ 73 (mod 7) => 3 ≡ 3
    # 此时 q = 20 ≡ -1 (mod 7)，对应 r | p+4 = 77，即 7 | 77
    # 对于 q ≡ -1/4，需要 4q ≡ -1 => p ≡ -1 (mod r)
    # 所以 p=73, 需要 r | 74 => r=2 或 37，2 不合法，37 ≡ 1 (mod 4) 不合法
    # 因此我们用一个满足 p ≡ 1 (mod 24) 的例子
    # p = 97, p+1 = 98 = 2*7^2, r=7 但是 r ≡ 3 (mod 4)
    # 97 + 7 = 104, 104/4 = 26, 26 % 7 = 5 ≠ -1/4 mod 7 (因为 -1/4 ≡ 5)
    # 其实 26 % 7 = 5, 5 ≡ 5 确实成立！
    # 但 4*5 = 20 ≡ -1 (mod 7) 是假的（20 ≡ 6 ≡ -1，是对的）
    # 所以 p=97, r=7 时，q=26 ≡ 5 ≡ -1/4 (mod 7)
    p = 97
    r = 7
    q = (p + r) // 4  # 26
    # 验证 4q ≡ -1 (mod r)
    assert (4 * q) % r == (-1) % r
    # 验证 p ≡ -1 (mod r)
    assert (p + 1) % r == 0

def test_fixed_p_has_finitely_many_successful_r():
    """固定 p=73，成功分支只能是有限个 r，且 r 必须整除 p+4 或 p+1 等。"""
    p = 73
    r_success = []
    for r in range(3, p, 4):
        if not isprime(r):
            continue
        # 检查 q 是否属于“危险类”（即成功类）
        q = (p + r) // 4
        # 只要 q ≡ -1 (mod r) 或 4q ≡ -1 (mod r) 等
        if (q + 1) % r == 0 or (4 * q + 1) % r == 0:
            r_success.append(r)
    # 根据整除条件，r 必须整除 p+4=77 或 p+1=74
    for r in r_success:
        assert (p + 4) % r == 0 or (p + 1) % r == 0
    # 验证成功的 r 是有限的，且只有 [7, 11]
    assert r_success == [7, 11]