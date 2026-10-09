# 项目状态 · 数论定理自动证明系统

## 项目地址
https://github.com/gzchengzhi/numbertheoryMCS

## 理论基础
- Cheng, Z. (2012). On Construction of a Mini Chinese Language System...
- Cheng, Z. (2019). Cognitive Development Theory, Ch.8.

## 核心架构
L1 符号层 / L2 概念层 / L3 定理层 / L4 检索层 / L5 计算层

## 系统规模
- 424 条定理（10 模块）
- 3 种证明策略（直接 / 反证 / 归纳）
- 20 个计算函数
- 零依赖 + 零幻觉

## 关键文件
- numtheory_prover.py   ← 核心证明器
- arithmetic_engine.py  ← 计算引擎
- theorem_store.py      ← 定理库管理
- adaptive_store.py     ← 自适应学习
- adaptive_prover.py    ← 自适应证明
- nl_interface.py       ← 自然语言接口
- app.py                ← Web 界面
- theorems/*.jsonl      ← 424 条定理

## 已完成能力
- ✅ 直接证明
- ✅ 反证法
- ✅ 数学归纳法
- ✅ 带前提证明
- ✅ 多中间子目标（12 级递归）
- ✅ α-转换（变量重命名）
- ✅ Skolem 常量
- ✅ 计算引擎
- ✅ 自适应学习
- ✅ 自然语言接口（本地 Qwen 3.0-4B）

## 已知局限
- 构造性问题（如"两位数乘9数字和不变"）无法处理
- 列表/递归参数不支持
- 仅 Horn 子句
- 9 个奇数之和偶尔失败（max_depth 限制）

## 当前状态
v8.0：多中间子目标链完成
- 7 个奇数之和 ✅（12 级递归链）
- 9 个奇数之和 ⚠️（偶尔失败）

## 下一轮目标
1. 扩展到一般数论题
2. 竞赛题求解
3. 列表/递归支持
4. 更多证明策略