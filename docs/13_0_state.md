# numbertheoryMCS 13.x 最终状态（2026-11-01）

## 13.x 基线
- 主库神经元: 212
- 域神经元: dirichlet 5 + elliptic 5 = 10
- 总神经元: 222
- bench_competition: 119/120 NEURON (99.2%)
- pytest: 119 passed + 1 xfailed
- domains: dirichlet 5/5 + elliptic 5/5 = 10/10

## 13.x 进度
| 阶段 | pass/120 | 状态 |
|---|---|---|
| 13.0.1 | 107 | ✅ 概念域注册 |
| 13.0.2 | 109 | ✅ 构造性推理（C028/C111） |
| 13.0.3 | 114 | ✅ Dirichlet 5/5 |
| 13.0.4 | 119 | ✅ 椭圆曲线 5/5 |
| 13.0.5 | 119 → 120 | C096 构造性存在（未完成） |

## 13.x 的域机制
- `concept_domain.py`：`ConceptDomain` + `DomainRegistry`
- `domains/dirichlet/`：5 神经元 + 5 题
- `domains/elliptic/`：5 神经元 + 5 题
- `bench_competition.py` 和 `test_12_bench.py` 都加载 `domains/`

## 13.x 的新开关
- `ENABLE_EMPTY_LOWER`（默认 False，bench/test 打开）——`lower=[]` 时返回 True（C028）

## 唯一 fail：C096
- 构造性存在，`_try_recursive` 返回 None 谜团
- `S::pythagorean` 的 `construct` 字段已加，但 `_try_recursive` 没遍历到
- 需要命令行逐行 debug `_indexed_try_recursive`
- 留 13.0.5 或 14.0

## 13.x 的技术栈
- 图式层（_try_recursive + _try_activate_neurons）
- 同构迁移（iso_edges）
- 计算层（_try_sympy）
- 回退层（Prover 链式搜索）
- 性能索引（_indexed_try_recursive + _indexed_activate）
- 假阳性防御（_check_subst_consistency）
- 构造性存在（construct 字段）
- 域注册机制（ConceptDomain + DomainRegistry）
- 空 lower 支持（ENABLE_EMPTY_LOWER）