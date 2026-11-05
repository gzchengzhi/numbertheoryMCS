# numbertheoryMCS 16.0 状态（内部里程碑，不发布）

## 定位

16.0 是内部里程碑，**不发布**。发布门槛：

- 能对**任意**新题自主完成多步骤证明（不依赖手工补丁）
- 证明失败时自动诊断「缺什么神经元」并自动学习，不需要人工 Y/N
- `DeepRecursiveProver` 单题 < 0.1 秒，不慢

16.0 做到：
- 200/200（100%）保持，T004/T005 假阳性消除
- 失败驱动神经元生成（交互式 Y/N）
- 新题自诊断（`tools/diagnose.py`）
- 语义约束（`semantic_guard` + `GuardedProver`）

16.0 没做到：
- `DeepRecursiveProver` 慢（单题 2s），默认关，`USE_DEEP=1` 才用
- `_auto_learn` 自动合入慢且假阳性多，默认关
- `diagnose` 只诊断不自动学

## 交付

| 阶段 | 内容 | 验收 |
|---|---|---|
| 16.0.1 | `semantic_guard.py` 语义约束 | 6 passed |
| 16.0.2 A | `guarded_prover.py` T004/T005 假阳性消除 | 5 passed，200/200 |
| 16.0.2 B | `learn_from_failure.py` 交互式 Y/N | fallback 18→16 |
| 16.0.3 | `suggest_candidates` + `_auto_learn`（实验性） | 13 passed |
| 16.0.4 | `tools/diagnose.py` 新题自诊断 | 2 passed |

## 基线

- 回归：120 + 11 = 131 passed（13.x 不退化）
- 15.0 新测试：6 + 14 + 9 + 5 = 34 passed
- 16.0 新测试：6 + 5 + 13 + 2 = 26 passed
- 合计：191 passed
- 竞赛题：200/200 (100%)，simple 200/200 (100%)
- `suspect: 0`，`fail: 0`，`fallback: 16`
- 神经元：213 主库 + 10 域 + 6 phi 补丁 + 2 learned + 61 verified + 50 N=2 + 385 N=3 = 727

## 已知边界

- `fallback 16`：10 `sympy` + 6 `direct`，合法回退
- `DeepRecursiveProver` 慢（2s/题），`ENABLE_SUBGOAL_SPLIT` 深度 8 时指数，默认关
- `_auto_learn` 自动合入假阳性多（X174 的 `gcd*lcm=a*b <- gt(a,0),gt(b,0)`），默认关
- `diagnose` 对现有 200 题全成功，失败路径用空 store 测

## 距发布（17.0）还差什么

1. **`DeepRecursiveProver` 提速**：`_try_subgoal_split` 的 `retrieve_adaptive` 全候选改索引，`get_cooccur_neighbors` 用 `_adj_index` 替代 O(E)，单题从 2s 降到 0.1s。
2. **`_auto_learn` 假阳性防御**：`verify_by_structure` + `sympy` 之外，加「`lower` 和 `head` 谓词有交集」规则（X123 的 `divides <- equals` 被误合入，但语义上 `equals(a, b*q+0)` 推 `divides(b, a)`，是真定理；X174 的 `gcd*lcm=a*b <- gt` 是假定理）。
3. **`diagnose` 自动学**：失败 → 候选 → 自动验证 → 自动合入，去掉人工 Y/N。
4. **新题 benchmark**：200 题之外的 50 道新题（从竞赛题、教材题、IMO 题里挑），`diagnose` 自动学，pass 率 ≥ 90%。

这四个是 17.0 的门槛，16.0 只是把骨架搭好。