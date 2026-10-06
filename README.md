# 数论定理自动证明器 · Mini Theorem Prover

> **零依赖、可解释、自适应**的数论定理自动证明系统。
> 基于**分层联想网络**（Hierarchical Associative Network），
> 支持**直接证明 / 反证法 / 数学归纳法**三种策略。

输入 `irrational(sqrt(2))`，输出完整的证明链：
[1] 应用「素数平方根无理性」（T018）
前提: prime(2)
结论: irrational(sqrt(2))
[2] 应用「2是素数」（T020）
结论: prime(2)

---

## ✨ 特点

- **零第三方依赖**：纯 Python 标准库，无需 `pip install`
- **可解释**：每一步证明都能追溯到具体定理
- **自适应**：定理权重 + 共现边学习，越用越快
- **多策略**：直接证明、反证法、数学归纳法
- **理论完整**：基于作者 2012 年论文 + 2019 年专著

---

## 🏗️ 架构
┌─────────────────────────────────────────────┐
│ 用户输入：irrational(sqrt(2)) │
└────────────────┬────────────────────────────┘
↓
┌────────┴────────┐
│ L4 检索层 │ ← PMI + 共现边 + 权重
│ top-K 相关定理 │
└────────┬────────┘
↓
┌────────┴────────┐
│ Prover 核心 │ ← SLD 归结 + 合一
│ 三种策略 │
└────────┬────────┘
↓
┌────────┴────────┐
│ 证明链输出 │
└─────────────────┘

### 四层设计

| 层 | 功能 | 对应文件 |
|---|---|---|
| **L1 符号层** | 数学符号规范化（`\|`、`≡`、`gcd`） | `numtheory_prover.py` |
| **L2 概念层** | 28 个数论概念（素数、整除、同余……） | `numtheory_mvp.py` |
| **L3 定理层** | 68 条定理的 Horn 子句表示 | `theorem_store.py` |
| **L4 检索层** | 自适应检索 + 共现边学习 | `adaptive_store.py` |

---

## 📚 理论基础

本项目基于 **概念三角形（Concept Triangle）** 和 **微型汉语系统（Mini Chinese Language System）**，
详见作者的两篇学术文献：

### [1] Cheng, Z. (2012). *On Construction of a Mini Chinese Language System and Automatic Generation of Articles*. 中国科技论文在线. http://www.paper.edu.cn

**核心贡献**：
- 提出**微型汉语系统**，用 16 个汉字描述生态系统
- 定义**概念三角形**：两个下层概念激活一个上层概念
- 通过**句子强度**公式判断句子意义
- 自动生成文章的完整规则层

### [2] Cheng, Z. (2019). *Cognitive Development Theory*. American Academic Press, Ch.8, 188–206.

**核心贡献**：
- 将概念三角形理论扩展到**形式运算阶段**认知
- 分析概念数量对认知模式的影响
- 提出**注意力控制**与**能量消耗**关系

### 本项目的延伸

将上述理论从**汉语系统**推广到**数论知识系统**：

| 原理论 | 本项目 |
|---|---|
| 汉字神经元 | 数论概念（素数、整除……） |
| 概念三角形 | Horn 子句（前提 → 结论） |
| 连接强度 | 定理权重 + 共现边 |
| 句子强度 | 检索打分 |
| 联想机制 | 自适应检索 + fallback |

---

## 🚀 快速开始

### 环境要求

- Python 3.7+
- 零第三方依赖（Web 界面可选 Flask）

```bash
python --version   # 确认版本
基础用法
# 1. 直接证明
python numtheory_prover.py --prove "prime(3)"

# 2. 反证法
python numtheory_prover.py --prove "prime_infinite" --strategy contradiction

# 3. 数学归纳法
python numtheory_prover.py --prove "sum_to_n(k, S)" --strategy induction --var k

# 4. 自适应证明（带权重学习）
python adaptive_prover.py --prove "irrational(sqrt(2))"

# 5. 批量 benchmark
python adaptive_prover.py --prove "prime(3)" --benchmark

# 6. Web 界面
pip install flask
python app.py
# 浏览器打开 http://127.0.0.1:5000
📖 示例
示例 1：√2 无理性
python numtheory_prover.py --prove "irrational(sqrt(2))"
示例 2：素数无穷多（反证法）
python adaptive_prover.py --prove "prime_infinite" --strategy contradiction
输出 9 步完整反证链：
[1] 推出矛盾 (T058)
  [2] p!+1有素因子q (T057)
    [3] 构造p!+1 (T056)
      [4] 有限素数有最大者 (T055)
      [5] 假设素数有限 (T054)
      [6] 假设 not_prime_infinite (ASSUME)
  ...
证明成功
示例 3：前 n 项和（数学归纳法）
python adaptive_prover.py --prove "sum_to_n(k, S)" --strategy induction --var k
输出：
[归纳法] 基例: sum_to_n(1,S)
[归纳法] 基例成功
[归纳法] 归纳步成功

证明链:
[1] 1到1的和 (T059)
[2] 归纳假设形式 (T067)

证明成功：sum_to_n(k,S)

🧠 自适应学习
系统会在使用中自动学习：

1. 定理权重
证明成功 → 链上定理权重 +0.1

证明失败 → 尝试过的定理权重 -0.05

2. 共现边
证明成功 → 链上所有定理对的共现边 +0.15

下次检索时，沿共现边扩展，把"证明链上会用到但直接匹配不上的"定理也拉进来

效果
看 benchmark 的第 1 次 vs 第 3 次：

目标	第 1 次	第 3 次
prime(3)	Round 0 成功	Round 0 成功
irrational(sqrt(2))	fallback 成功	Round 0 成功
sum_to_n(k,S)	Round 0 成功	Round 0 成功
关键证据：irrational(sqrt(2)) 从"需要 fallback"变成"第一轮直接成功"——
因为系统学到 T018 和 T020 之间有强共现边。

📁 项目结构
text
mini-theorem-prover/
├── numtheory_prover.py      # 核心证明器（L1+L3）
├── numtheory_mvp.py          # L4 概念检索
├── theorem_store.py          # 定理库管理
├── adaptive_store.py         # 自适应层（权重 + 共现边）
├── adaptive_prover.py        # 自适应证明器
├── smart_prover.py           # 智能证明器
├── export_theorems.py        # JSONL 导出工具
├── theorems.jsonl            # 定理库（68 条）
├── app.py                    # Web 后端
├── templates/index.html      # Web 前端
├── static/style.css
├── README.md
├── ROADMAP.md
├── paper.md                  # 技术报告
├── LICENSE                   # CC BY-NC 4.0
└── .gitignore
📊 系统规模
指标	数值
定理数	68 条
概念数	28 个
谓词数	29 个
证明策略	3 种
平均证明深度	2-4 步
最复杂证明	9 步（素数无穷多）
代码规模	~2000 行
依赖	0（核心）/ Flask（Web）
🛣️ 路线图
✅ v1.0 直接证明 + 合一 + SLD 归结

✅ v2.0 反证法 + 数学归纳法

✅ v3.0 自适应检索 + 共现边学习

✅ v3.1 Web 界面

🚧 v4.0 扩展到 200+ 定理

🔮 v5.0 概念三角形显式表示

🔮 v6.0 自然语言接口

📜 许可
算法与架构：CC BY-NC 4.0（署名 + 禁止商用）

引用要求：使用本项目请引用 [1] 和 [2]

详见 LICENSE

📚 引用
bibtex
@article{cheng2012mini,
  title={On Construction of a Mini Chinese Language System and Automatic Generation of Articles},
  author={Cheng, Z.},
  journal={中国科技论文在线},
  year={2012},
  url={http://www.paper.edu.cn}
}

@book{cheng2019cognitive,
  title={Cognitive Development Theory},
  author={Cheng, Z.},
  publisher={American Academic Press},
  chapter={8},
  pages={188--206},
  year={2019}
}
🙏 致谢
理论来源：作者本人的两篇学术文献

工程灵感：Retrieval-Pretrained Transformer (TACL 2024)、MLP Memory (ICLR 2025)

📮 联系方式
学术合作 / 商业授权：GitHub Issues

问题反馈：GitHub Issues