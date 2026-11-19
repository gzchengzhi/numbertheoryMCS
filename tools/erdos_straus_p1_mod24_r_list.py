# tools/erdos_straus_p1_mod24_r_list.py
from sympy import isprime

def generate_r_list(r_max: int) -> list:
    """生成 r ≤ r_max, r ≡ 3 (mod 4) 的素数列表。"""
    return [r for r in range(3, r_max + 1, 4) if isprime(r)]

if __name__ == "__main__":
    r_list = generate_r_list(200)
    print(f"r ≤ 200: {len(r_list)} 个素数")
    print(r_list)