# numbertheoryMCS

数论定理自动证明系统——基于**概念三角形**的检索层。

**理论基础**：
- 程智. 微型汉语系统的构建及汉语文章的自动生成. 2012.
- 程智. 认知发展理论. 2019. 第 8 章"形式运算"

## 核心思想

传统 ATP 穷举所有定理 → 计算复杂度指数爆炸。

本系统：
- **全互联网络**：所有定理两两有边，初始 ε
- **概念三角形**：`A + B → C`，边权 `0.5^(N-1)`
- **一次性学习**：不训练、不迭代，权值一次写定
- **检索层 + 计算层分离**：检索层按连接权重排序候选，计算层做 unify / 递归

## 已验证案例
类型	例子	结果
同谓词传递	congruent(a,c,m) ← congruent(a,b,m), congruent(b,c,m)	✓ 链长 3
多层嵌套	四层同余传递	✓ 链长 7
变体型	congruent(b,a,m) ← congruent(a,b,m)	✓ 链长 2
跨谓词组合	divides(factorial(n), product_range(m,n))	✓ 链长 5
素数无穷	prime_infinite	✓
无理数	irrational(sqrt(2))	✓

1. 端到端样例学习（不需要 LLM）
bash
python test_learn_and_prove.py
预期输出：

text
[OK] 证明成功！链长 5
  1. T_EQUAL_SUBST  等量代换
  2. T_PROD_RANGE_EQ  连续整数乘积公式
  3. T_MUL_DIVIDES  整数乘积整除性
  4. T_FACT_INT  阶乘整性
  5. T_BINOM_INT  组合数整性
2. Web 界面（需要本地 Qwen）
先启动本地 Qwen（llama.cpp server）：

bash
# 例：llama.cpp 加载 qwen3-4b
./llama-server -m qwen3-4b.gguf --port 8080
再启动 Web 服务：

bash
python app.py
浏览器打开 http://127.0.0.1:5000

支持：

形式化输入：直接写谓词

自然语言输入：中文 + 本地 Qwen 解析

自动学习：LLM 返回的新定理自动吸收

已验证案例
类型	例子	结果
同谓词传递	congruent(a,c,m) ← congruent(a,b,m), congruent(b,c,m)	✓ 链长 3
多层嵌套	四层同余传递	✓ 链长 7
变体型	congruent(b,a,m) ← congruent(a,b,m)	✓ 链长 2
跨谓词组合	divides(factorial(n), product_range(m,n))	✓ 链长 5
素数无穷	prime_infinite	✓
无理数	irrational(sqrt(2))	✓
跨谓词组合的证明链：

text
目标: divides(factorial(n), product_range(m, n))
  └─ T_EQUAL_SUBST              ← 等量代换
       ├─ T_PROD_RANGE_EQ        ← 连续乘积公式
       └─ T_MUL_DIVIDES          ← 整数乘积整除性
            ├─ T_FACT_INT        ← 阶乘整性
            └─ T_BINOM_INT       ← 组合数整性
架构
text
┌─────────────────────────────────┐
│ L4 检索层（概念三角形）           │
│ · 节点：定理                     │
│ · 边：概念三角形                 │
│ · 权值：0.5^(N-1)               │
│ · 学习：吸收新定理 → 标记 → 加成  │
└──────────────┬──────────────────┘
               │ 候选列表（按权值排序）
               ▼
┌─────────────────────────────────┐
│ L5 计算层（ATP）                 │
│ · unify / 递归 / 反证 / 归纳      │
│ · 符号不等式 / 计算引擎           │
└─────────────────────────────────┘
目录结构
text
numbertheoryMCS/
├── numtheory_prover.py       # Horn 子句证明器
├── adaptive_store.py         # 全互联网络 + 概念三角形
├── adaptive_prover.py        # 学习 + 检索 + 证明
├── theorem_store.py          # 定理库基础
├── symbolic.py               # 符号推理
├── arithmetic_engine.py      # 计算引擎
├── nl_interface.py           # 自然语言接口（Qwen）
├── app.py                    # Flask Web 服务
├── test_learn_and_prove.py   # 端到端测试
├── theorems/                 # 定理库（JSONL）
│   ├── basic.jsonl
│   ├── m1.jsonl
│   ├── ...
│   └── learned.jsonl         # 学习积累的定理
├── templates/
│   └── index.html            # Web 界面
├── requirements.txt
├── LICENSE
└── README.md
与 ATP 的关系
本系统不替代 ATP —— 在 ATP 之上加检索层：

ATP：负责 unify / 递归 / 反证 / 归纳（计算层）

概念三角形：负责排序候选（检索层）

两层独立运行：

检索层只给"先试谁"

计算层只给"能不能证"

不耦合

这正是 Cheng 2012 / 2019 的"层次化"思想：

与数学语言系统和自然语言系统相比，计算机语言系统介于数学语言系统和自然语言系统之间。

引用
bibtex
@article{cheng2012mcs,
  title={微型汉语系统的构建及汉语文章的自动生成},
  author={程智},
  year={2012}
}

@book{cheng2019cognitive,
  title={认知发展理论},
  author={程智},
  year={2019},
  chapter={8}
}
License
MIT


## 快速开始

```bash
pip install -r requirements.txt
python test_learn_and_prove.py

