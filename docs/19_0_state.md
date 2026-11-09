# 19.0 状态（19.0.1 – 19.0.5）

## 已完成（符号证明）

### 19.0.1 单位分数证明
- `tools/unit_fraction.py`：`find_egyptian_3_terms` / `scale_equation` / `extract_n` / `verify_unit_fraction` / `solidify_unit_fraction`。
- `theorems/18_0_unit_fraction.json`：删 `construct`，`lower=["gt(n,0)"]`，`head_pattern=["unit_fraction_sum",["x","y","z","n"]]`。
- `tests/test_19_unit_fraction.py`：12 passed。
- 关键：`1/n = 1/(2n)+1/(3n)+1/(6n)`，外围 sympy 验证，不碰 `_verify_construct`。

### 19.0.2 Erdős–Straus 条件归约
- `tools/erdos_straus.py`：`verify_ep_instance` / `verify_reduction_identity` / `verify_reduction_from_ep` / `verify_mod4_zero`。
- 定理：EP（p ≤ 10^17，引用 Salez 2014）⟹ `4/(pk) = 1/(ak)+1/(bk)+1/(ck)`。
- `tests/test_19_erdos_straus.py`：13 passed。
- **不声称 EP 为真，只验证归约的每个实例。**

### 19.0.3 p ≡ 3 (mod 4)
- `tools/erdos_straus_mod4.py`：`generate_candidates` / `filter_candidates` / `try_candidate` / `find_optimal_candidate` / `verify_all_p3_mod4` / `solidify_candidate`。
- `theorems/19_0_p3_mod4.json`：3 个通用规则神经元（`congruent_add_same` / `congruent_sub_same` / `integer<-congruent_div`）。
- 构造：`a = (p+1)/4`，`m = p(p+1)/4`，`b = m+1`，`c = m(m+1)`。
- `tests/test_19_erdos_straus_mod4.py`：15 passed。

### 19.0.4 p ≡ 5 (mod 12)
- `tools/erdos_straus_p1_3overp.py`：`construction_p5_mod12` / `verify_p5_mod12` / `verify_all_p5_mod12`。
- 构造：`3/p = 1/((p+1)/3) + 1/(p(p+1)/3)`，`4/p = 1/p + 3/p`（三项）。
- `tests/test_19_erdos_straus_p1_3overp.py`：10 passed。

### 19.0.5 p ≡ 13 (mod 24)
- `tools/erdos_straus_p13_mod24.py`：`construction_p13_mod24` / `verify_p13_mod24` / `verify_all_p13_mod24`。
- 构造：`4/p = 4/(p+3) + 24/(p(p+2)(p+3)) + 12/((p+2)(p+3))`。
- 即 `(x, y, z) = ((p+3)/4, p(p+2)(p+3)/24, (p+2)(p+3)/12)`。
- `tests/test_19_erdos_straus_p13_mod24.py`：12 passed。

## 覆盖状态

| 类 | 比例 | 状态 |
|---|---|---|
| p ≡ 3 (mod 4) | 50% | 符号证明（19.0.3） |
| p ≡ 5 (mod 12) | 25% | 符号证明（19.0.4） |
| p ≡ 13 (mod 24) | 12.5% | 符号证明（19.0.5） |
| **合计** | **87.5%** | **符号证明** |
| p ≡ 1 (mod 24) | 12.5% | 数值验证 143/143（19.0.6 探测），符号构造未完成 |

**87.5% 是复现 Mordell 1969 归约已覆盖的类，不是“首次覆盖”，不是“世界纪录”。** 计算验证上限（Salez 10^17）是另一回事。

## 19.0.6 探测（未固化）

- `tools/erdos_straus_p1_mod24.py`：`try_r_c` / `find_construction_p1_mod24` / `verify_all_p1_mod24`。
- p ≤ 10^4 的 p ≡ 1 (mod 24) 素数 143/143 有数值解。
- `d`（`N²` 的因子）无统一符号表达式，**不是证明**。
- 未写正式测试，未固化神经元。

## 纪律

- 不碰 18.0 稳定层（`deep_recursive_prover.py` / `recursive_prover.py` / `adaptive_store.py` / `numtheory_prover.py`）。
- 外围模块 + 公开接口 + 独立测试。
- 196 回归 gate + 200/200 竞赛题基线不能降。