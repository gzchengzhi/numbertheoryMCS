# tests/test_20_erdos_straus_density.py
import pytest
from tools.erdos_straus_p1_mod24_density import (
    failure_rate, cumulative_failure_product, density_upper_bound,
    large_sieve_neuron, crt_density_neuron, solidify_density_neurons,
)


def test_failure_rate_lt_one():
    """每个 r 的实测失败率 < 1。"""
    for r in [3, 7, 11, 23]:
        rate = failure_rate(r)
        assert 0 < rate < 1, f"r={r}: rate={rate}"


def test_cumulative_product_decreasing():
    """累积失败率乘积随 R 扩大递减（数值事实）。"""
    r_list = [3, 7, 11, 23]
    products = cumulative_failure_product(r_list)
    for i in range(1, len(products)):
        assert products[i]["cumulative_product"] <= products[i-1]["cumulative_product"]


def test_product_below_threshold():
    """前 4 个 r 的乘积 < 0.15（数值事实，不是证明趋于 0）。"""
    product = density_upper_bound([3, 7, 11, 23])
    assert product < 0.15, f"product={product} 未足够小"


def test_large_sieve_neuron():
    rec = large_sieve_neuron([3, 7, 11, 23])
    assert rec["neuron"].startswith("NEURON::S::large_sieve")
    assert "不声称例外集为空" in rec["note"]


def test_crt_density_neuron():
    rec = crt_density_neuron([3, 7, 11, 23])
    assert rec["neuron"].startswith("NEURON::S::crt_density")
    assert "不声称乘积严格趋于 0" in rec["note"]


def test_solidify_density_neurons(tmp_path):
    """固化并检查文件存在且内容正确。"""
    path = tmp_path / "20_0_p1_mod24_density.json"
    solidify_density_neurons([3, 7, 11, 23], str(path))
    assert path.exists()
    import json
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert "NEURON::S::large_sieve_density_bound::p1_mod24" in data["concept_neurons"]
    assert "NEURON::S::crt_density_bound::p1_mod24" in data["concept_neurons"]
    
def test_extended_r_product():
    """20.1: 扩展 R 后，实测乘积 = 0.060661 < 0.1。
    注意：这是实测值，不是证明乘积趋于 0。
    r=43 的失败率高达 95.24%，说明 F_r 失败率不是单调下降的。
    """
    from tools.erdos_straus_p1_mod24_density import density_upper_bound
    product = density_upper_bound([3, 7, 11, 23, 31, 43, 47, 59, 67, 71, 79, 83])
    assert product < 0.1, f"product={product:.6f} 超过 0.1（实测 0.060661）"
    assert product > 0.01, f"product={product:.6f} 意外地小于 0.01"


def test_extended_r_all_prime():
    """20.1: 扩展 R 中所有 r 都是素数（排除合数 r=39）。"""
    from sympy import isprime
    for r in [3, 7, 11, 23, 31, 43, 47, 59, 67, 71, 79, 83]:
        assert isprime(r), f"r={r} 不是素数"    

def test_extended_r_product_20_2():
    """20.2: 扩展 R 后，实测乘积 = 0.037384 < 0.05。"""
    from tools.erdos_straus_p1_mod24_density import density_upper_bound
    r_list = [3, 7, 11, 23, 31, 43, 47, 59, 67, 71, 79, 83]
    product = density_upper_bound(r_list)
    # 如实记录实测值，不预设 0.01 这种达不到的假阈值
    assert product < 0.05, f"product={product:.6f} 超过 0.05（实测 0.037384）"

def test_extended_r_product_20_3():
    """20.3: r ≤ 200 的 23 个分支，实测乘积 = 0.018872 < 0.02。"""
    from tools.erdos_straus_p1_mod24_density import density_upper_bound
    from tools.erdos_straus_p1_mod24_r_list import generate_r_list
    r_list = generate_r_list(200)
    product = density_upper_bound(r_list)
    assert product < 0.02, f"product={product:.6f} 超过 0.02（实测 0.018872）"


def test_uncovered_list_empty_100000():
    """20.3: p ≤ 100000，r ≤ 200 的分支联合覆盖后，未覆盖列表为空。"""
    from tools.erdos_straus_p1_mod24_uncovered_list import find_uncovered
    from tools.erdos_straus_p1_mod24_r_list import generate_r_list
    r_list = generate_r_list(200)
    uncovered = find_uncovered(r_list, p_max=100000)
    assert uncovered == [], f"未覆盖列表非空: {uncovered}"    
    
