# tools/erdos_straus_p1_mod24_min_r.py
"""20.4: 对每个 p ≡ 1 (mod 24)，找最小成功 r，拟合 r ~ C p^α，并绘制曲线。"""
import math
import json
import time
from sympy import isprime
from tools.erdos_straus_p1_mod24_symbolic import branch_succeeds


def find_min_r(p, r_max=None):
    """找最小的 r ≡ 3 (mod 4) 素数，使分支成功。"""
    if r_max is None:
        r_max = p
    for r in range(3, min(r_max, p), 4):
        if not isprime(r):
            continue
        if branch_succeeds(p, r, c=4):
            return r
    return None


def collect_min_r(p_max=100000, verbose=True):
    results = []
    start = time.time()
    for p in range(25, p_max + 1, 24):
        if not isprime(p):
            continue
        r_min = find_min_r(p)
        if r_min is not None:
            results.append({"p": p, "r_min": r_min})
        if verbose and len(results) % 500 == 0:
            elapsed = time.time() - start
            print(f"  已处理 {len(results)} 个 p，耗时 {elapsed:.1f}s")
    elapsed = time.time() - start
    print(f"收集完成: {len(results)} 个 p，总耗时 {elapsed:.1f}s")
    return results


def fit_alpha(results):
    """拟合 log r_min = alpha * log p + beta。"""
    xs = [math.log(r["p"]) for r in results]
    ys = [math.log(r["r_min"]) for r in results]
    n = len(xs)
    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xx = sum(x*x for x in xs)
    sum_xy = sum(x*y for x, y in zip(xs, ys))
    denom = n * sum_xx - sum_x * sum_x
    if denom == 0:
        return None, None
    alpha = (n * sum_xy - sum_x * sum_y) / denom
    beta = (sum_y - alpha * sum_x) / n
    return alpha, beta


def plot_min_r(results, output_path="theorems/20_4_min_r_curve.png"):
    """绘制 r_min vs p 的曲线（双对数坐标）。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib 未安装，跳过绘图。请运行: pip install matplotlib")
        return None

    ps = [r["p"] for r in results]
    rs = [r["r_min"] for r in results]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # 左图: 双对数坐标
    ax = axes[0]
    ax.scatter(ps, rs, s=5, alpha=0.5, label="r_min(p)")
    # 参考线: p^0.5 和 p^1
    p_ref = [min(ps), max(ps)]
    ax.plot(p_ref, [p**0.5 for p in p_ref], "r--", label="p^0.5")
    ax.plot(p_ref, [p**1.0 for p in p_ref], "g--", label="p^1.0")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("p")
    ax.set_ylabel("r_min")
    ax.set_title("r_min vs p (log-log)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 右图: 比值 r_min / p
    ax = axes[1]
    ratios = [r["r_min"] / r["p"] for r in results]
    ax.scatter(ps, ratios, s=5, alpha=0.5)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("p")
    ax.set_ylabel("r_min / p")
    ax.set_title("r_min / p vs p")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    print(f"曲线已保存到 {output_path}")
    return output_path


if __name__ == "__main__":
    import sys
    p_max = int(sys.argv[1]) if len(sys.argv) > 1 else 100000
    print(f"=== 收集 p ≤ {p_max} 的最小成功 r ===\n")
    results = collect_min_r(p_max)
    alpha, beta = fit_alpha(results)
    print(f"\n样本数: {len(results)}")
    print(f"拟合: r_min ≈ C * p^{alpha:.4f}")
    print(f"C = exp({beta:.4f}) = {math.exp(beta):.4f}")
    print(f"\nr_min 的统计:")
    rs = [r["r_min"] for r in results]
    print(f"  最小值: {min(rs)}")
    print(f"  最大值: {max(rs)}")
    print(f"  中位数: {sorted(rs)[len(rs)//2]}")
    ratios = [r["r_min"] / r["p"] for r in results]
    print(f"  r_min/p 最小值: {min(ratios):.6f}")
    print(f"  r_min/p 最大值: {max(ratios):.6f}")
    print(f"  r_min/p 中位数: {sorted(ratios)[len(ratios)//2]:.6f}")
    
    plot_min_r(results)
    with open("theorems/20_4_min_r_analysis.json", "w", encoding="utf-8") as f:
        json.dump({"alpha": alpha, "beta": beta, "results": results}, f, indent=2)
    print("结果已保存到 theorems/20_4_min_r_analysis.json")