# numbertheoryMCS 12.x 最终状态（2026-11-01）

## 12.x 基线
- concept_neurons: 211 个
- bench_competition: 107/120 NEURON (89.2%)
- pytest: 107 passed + 13 xfailed
- fallback/suspect/exc: 0/0/0

## 12.x 完整进度
| 版本 | pass/120 | 关键 |
|---|---|---|
| 12.7 | 99 (82.5%) | p-adic/连分数/二次型/φ(p^k) |
| 12.8 | 100 (83.3%) | P2 假阳性消除 + C084 |
| 12.9 | 102 (85%) | C093/C118 的 direct → neuron |
| 12.10 | 107 (89.2%) | Wilson/二项式/Lucas/gcd_iter/prime_infinite |

## 13.0 的议题
- Dirichlet 特征 + L 函数（5）：C098~C102
- 椭圆曲线群律 + Mordell-Weil + Hasse 界（5）：C103~C107
- C028：无 premises or 嵌套
- C096：构造性存在，`_try_recursive` 返回 None 谜团
- C111：forall 嵌套 product

## 12.x 的完整技术栈
- 图式层：_try_recursive（递归点火）+ _try_activate_neurons（图式激活）
- 同构迁移：iso_edges.json（2 条 structural）
- 计算层：_try_sympy（sympy 直接算）
- 回退层：Prover 链式搜索（direct/contradiction/induction）
- 性能：_indexed_try_recursive（head 索引）+ _indexed_activate（clause 索引）
- 假阳性防御：_check_subst_consistency（ENABLE_SUBST_CONSISTENCY 开关）
- 构造性存在：construct 字段（S::pythagorean）

## 12.x 的工程纪律
- 不改 11.0 源码（除 12.8/12.9 的 P2/C093/C118，有开关和回退）
- 单文件 theorems/12_0_competition.jsonl
- 单文件 tests/bench/competition/cases.jsonl
- add_neuron.py 安全加神经元
- learn_12_0.py 自动学习管线（discover + judge + commit）
- 回退脚本 tools/rollback_v11_0.py