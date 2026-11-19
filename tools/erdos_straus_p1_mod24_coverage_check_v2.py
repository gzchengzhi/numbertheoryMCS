# tools/erdos_straus_p1_mod24_coverage_check_v2.py
from tools.erdos_straus_p1_mod24_coverage_check import check_coverage
from tools.erdos_straus_p1_mod24_r_list import generate_r_list

r_list = generate_r_list(200)
for r in r_list:
    info = check_coverage(r, p_max=100000)
    if info["missing"]:
        print(f"r={r}: 缺失 {len(info['missing'])} 类: {info['missing'][:10]}...")
    else:
        print(f"r={r}: 覆盖完整 ({info['covered']}/{info['total_classes']})")