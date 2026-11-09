# numbertheoryMCS

**微型汉语系统（Micro Chinese System, MCS）的数论自动证明实现。**

基于 Cheng (2012)《微型汉语系统的构建》与 Cheng (2019)《认知发展理论》第 8 章「形式运算」的工程实现，用「概念三角形 + 递归点火 + 同构迁移 + solidify」做自动定理证明。

---

## 当前版本：19.0.5 — Erdős–Straus 87.5% 符号证明

| 类 | 比例 | 构造 |
|---|---|---|
| p ≡ 3 (mod 4) | 50% | `a = (p+1)/4`（19.0.3） |
| p ≡ 5 (mod 12) | 25% | `3/p = 1/((p+1)/3) + 1/(p(p+1)/3)`（19.0.4） |
| p ≡ 13 (mod 24) | 12.5% | `(x,y,z) = ((p+3)/4, p(p+2)(p+3)/24, (p+2)(p+3)/12)`（19.0.5） |
| **合计** | **87.5%** | **符号证明 + sympy 验证** |

**诚实边界**：87.5% 是复现 Mordell 1969 归约已覆盖的类，不是首次覆盖，不是世界纪录。`p ≡ 1 (mod 24)` 的 12.5% 仍开放（19.0.6 探测对 p ≤ 10^4 数值验证 143/143，但 `d` 无统一符号表达式，不是证明）。

---

## 核心能力

- **图式层**：概念三角形（A+B→C）直接点火，200/200 竞赛题 100% 命中，fallback 0，suspect 0
- **递归点火**：上层概念逐层递归（`@0-@0` → `@0-@1`）
- **同构迁移**：跨谓词图式迁移（`divides` ↔ `congruent`）
- **深递归 + 子目标分解**：`DeepRecursiveProver`，能量预算 `E = 2^(N-1)·δ`
- **多域架构**：数论 + Dirichlet 特征 + 椭圆曲线
- **自动学习**：`discover` + `judge` + `commit`
- **证明固化**：`solidify` 把成功路径固化成新神经元
- **假阳性防御**：`Prover` substitution 一致性 + `GuardedProver`（T004/T005 抑制）

## 理论对应（Cheng 2019 §8）

| 实现 | 理论 |
|---|---|
| 概念三角形 | §8.2.4 |
| 递归点火 | §8.2.4 上层概念逐层形成 |
| 同构迁移 | §8.2.4 重合三角形 |
| `energy = 2^(N-1)·δ` | §8.5.1 认知与能量消耗 |
| `WorkingMemory` | §8.5.2 主题指导法 |
| `GuardedProver` | §8.5.2 最大意义保留 |
| `diagnose` | §8.5.3 注意力控制 |

---

## 当前基线

| 指标 | 值 |
|---|---|
| 竞赛题 bench | **200/200 (100%)** |
| 回归测试 | **196 passed** |
| 19.0 测试 | **62 passed**（unit_fraction 12 + erdos_straus 13 + mod4 15 + p1_3overp 10 + p13_mod24 12） |
| 总神经元 | **725**（主库 213 + 域 10 + phi 6 + learned 2 + verified 61 + N=2 50 + N=3 385） |
| 假阳性 | 0 |
| fallback | 0 |

## 快速开始

```bash
pip install -r requirements.txt

# 竞赛题批量测试（预期 200/200）
python tools/bench_competition.py

# 回归测试
pytest tests/regression/test_12_bench.py -q
pytest tests/domains/ -q

# 19.0 Erdős–Straus 测试
pytest tests/test_19_unit_fraction.py tests/test_19_erdos_straus.py \
      tests/test_19_erdos_straus_mod4.py tests/test_19_erdos_straus_p1_3overp.py \
      tests/test_19_erdos_straus_p13_mod24.py -q