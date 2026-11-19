# tools/erdos_straus_p1_mod24_log_r_bisect.py
"""20.6: 二分搜索最小的 C，使得 r ≤ C ln(p) 覆盖 p ≤ 100000。"""
from tools.erdos_straus_p1_mod24_log_r_bound import log_r_uncovered


def find_min_C(p_max=100000, C_lo=1.0, C_hi=10.0, tol=0.1):
    """二分搜索最小的 C，使得未覆盖 = 0。"""
    while C_hi - C_lo > tol:
        C_mid = (C_lo + C_hi) / 2
        result = log_r_uncovered(p_max, C_mid)
        if result["uncovered_count"] == 0:
            C_hi = C_mid
        else:
            C_lo = C_mid
        print(f"C={C_mid:.2f}: uncovered={result['uncovered_count']}, "
              f"C_lo={C_lo:.2f}, C_hi={C_hi:.2f}")
    return C_hi


if __name__ == "__main__":
    C_min = find_min_C()
    print(f"\n最小 C（经验）: {C_min:.2f}")