# 16.0 教训

## 工程

1. `theorems/*.jsonl` 的 `glob` 会把候选文件（`16_0_candidates.jsonl`）当定理库加载，`_dict_to_clause` 找不到 `head` 报 `KeyError`。候选文件应放 `data/` 或改 `.json`。
2. `_parse_pattern` 的 `rstrip(")")` 去掉所有尾部 `)`，嵌套括号（`plus(times(b,q), 0)`）丢了内层 `)`。改用 `rest[:-1]` 只去最外层。
3. `DeepRecursiveProver` 单题 2s，`_try_subgoal_split` 递归深度 10，`MAX_RECURSIVE_DEPTH` 没拦住（`_try_subgoal_split` 里没检查）。`bench_competition.py` 主跑用 `RecursiveProver`，`DeepRecursiveProver` 用 `USE_DEEP=1` 显式开。
4. `_try_subgoal_split` 的 `retrieve_adaptive` 全候选 + `get_cooccur_neighbors` O(E)，深度 8 时指数。加 `MAX_NODES=100` + 候选上限 20。
5. `diagnose` 的失败路径测试用空 store（只加载 `concept_neurons.json`，不加载定理库），不依赖「真实未覆盖题」。

## 设计

6. `T004`/`T005` 假阳性：`divides(1,a)`/`divides(a,0)` 的 `Const` 可 unify 任意 `Var`。`GuardedProver` 在 `goal` 不是 `divides(1,_)`/`divides(_,0)` 时剔除 `T004`/`T005`。
7. `_auto_learn` 自动合入假阳性：`gcd*lcm=a*b <- gt(a,0),gt(b,0)` 的 `lower` 推不出 `head`。需加「`lower` 和 `head` 谓词有交集」规则。
8. `ENABLE_AUTO_LEARN` 默认关，`USE_DEEP` 默认关，`bench_competition.py` 主跑不变（200/200，22s）。

## 理论对应

9. `GuardedProver` 对应 Cheng 2019 §8.5.2「最大意义保留」的反面：全局恒真定理要抑制。
10. `diagnose` 对应 Cheng 2019 §8.5.3「注意力控制」：失败时聚焦到「缺什么神经元」。

## 未解（17.0）

11. `DeepRecursiveProver` 提速到 < 0.1s/题。
12. `_auto_learn` 假阳性防御（`lower`/`head` 谓词交集）。
13. `diagnose` 自动学（去 Y/N）。
14. 200 题之外的 50 道新题 benchmark。