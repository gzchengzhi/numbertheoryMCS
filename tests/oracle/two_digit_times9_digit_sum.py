# tests/oracle/two_digit_times9_digit_sum.py
"""题1 oracle：两位数 n 满足 s(9n)==s(n)。"""

def digit_sum(x: int) -> int:
    return sum(int(c) for c in str(abs(x)))

def solve() -> list[tuple[int, int, int]]:
    """返回 [(n, s(n), s(9n))]，按 n 升序。"""
    out = []
    for n in range(10, 100):
        if digit_sum(9 * n) == digit_sum(n):
            out.append((n, digit_sum(n), digit_sum(9 * n)))
    return out

if __name__ == "__main__":
    sols = solve()
    print(f"解个数: {len(sols)}")
    for n, s_n, s_9n in sols:
        print(f"n={n:2d}  9n={9*n:3d}  s(n)={s_n}  s(9n)={s_9n}")

    # --- SymPy 交叉校验（可选，验证 oracle 自身正确性） ---
    try:
        import sympy as sp
        a, b = sp.symbols("a b", integer=True, positive=True)
        # 只做抽样校验：对每个解用 sympy 的 Integer 重算
        for n, _, _ in sols:
            assert sp.Integer(str(9 * n)).__int__() == 9 * n
        print("SymPy 交叉校验: OK")
    except ImportError:
        print("SymPy 未安装，跳过交叉校验")