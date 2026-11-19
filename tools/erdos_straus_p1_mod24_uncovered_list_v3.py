# tools/erdos_straus_p1_mod24_uncovered_list_v3.py
from tools.erdos_straus_p1_mod24_uncovered_list import find_uncovered
from tools.erdos_straus_p1_mod24_r_list import generate_r_list

r_list = generate_r_list(200)
uncovered = find_uncovered(r_list, p_max=100000)
print(f"未覆盖素数数量: {len(uncovered)}")
print(f"未覆盖素数列表: {uncovered}")