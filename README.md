# numbertheoryMCS

微型汉语系统（Micro Chinese System, MCS）的数论自动证明实现。

## 理论来源

- Cheng, Z. (2012). 微型汉语系统的构建及汉语文章的自动生成. 广州大学.
- Cheng, Z. (2019). 认知发展理论: 第 8 章 形式运算.

## 核心能力

- **图式层**：概念三角形（A+B→C）的直接点火
- **递归点火**：上层概念的逐层递归（`@0-@0` → `@0-@1`）
- **同构迁移**：跨谓词的图式迁移（`divides` ↔ `congruent`）
- **多域架构**：数论 + Dirichlet 特征 + 椭圆曲线
- **自动学习**：`discover` + `judge` + `commit`
- **假阳性防御**：`Prover` substitution 一致性

## 当前基线

| 指标 | 值 |
|---|---|
| 竞赛题 bench | **120/120 (100%)** |
| 回归测试 | **120 passed** |
| 域测试 | **10 passed** |
| 总神经元 | 223（主库 213 + 域 10） |

## 运行竞赛题批量测试
bash
python tools/bench_competition.py
预期：120/120 (100%)。

## 运行回归测试
bash
pytest tests/regression/test_12_bench.py -q
pytest tests/domains/ -q
预期：120 passed + 10 passed。

## 目录结构
text
├── theorems/               # 定理库（15 主文件 + 12_0_competition.jsonl + concept_neurons.json）
├── domains/                # 概念域（dirichlet + elliptic）
├── data/iso_edges.json     # 同构边
├── tests/                  # 测试
│   ├── regression/         # 回归
│   ├── bench/competition/  # 120 题
│   └── domains/            # 域测试
├── tools/                  # 工具脚本
├── docs/                   # 文档
└── *.py                    # 核心源码
## 核心源码
文件	作用
numtheory_prover.py	数论定理证明器（Prover、Pred、HornClause）
theorem_store.py	定理库存储
adaptive_store.py	自适应存储（神经元、共现、依赖）
adaptive_prover.py	自适应证明器（图式激活、链式回退）
recursive_prover.py	递归点火 + 同构迁移
concept_domain.py	概念域注册（ConceptDomain + DomainRegistry）
concept_triangle.py	概念三角形（extract_triangles）
working_memory.py	主题指导法
probe.py	可观测性
symbolic.py	符号不等式
sympy_bridge.py	sympy 翻译
sympy_decls.py	sympy 谓词声明
arithmetic_engine.py	计算引擎
## 理论对应
实现	Cheng 2019 §8
概念三角形	§8.2.4 概念三角形
递归点火	§8.2.4 上层概念逐层形成
同构迁移	§8.2.4 重合三角形
energy = 2^(N-1)·δ	§8.5.1 认知与能量消耗
WorkingMemory	§8.5.2 主题指导法
## 开发历程
版本	pass/120	关键
12.0	36/50 (72%)	基础图式
12.5	79/80 (98.75%)	二次剩余/完全数/无理数
12.10	107 (89.2%)	Wilson/二项式/Lucas
13.0.2	109 (90.8%)	C028 + C111
13.0.3	114 (95%)	Dirichlet
13.0.4	119 (99.2%)	椭圆曲线
13.0.5	120/120 (100%)	C096（扁平 and）

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt