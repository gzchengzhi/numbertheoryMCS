"""
自然语言接口：中文 → 形式化目标 → 证明

依赖：
  pip install openai  (或 dashscope、requests)

用法：
  python nl_interface.py --query "证明根号2是无理数"
  python nl_interface.py --interactive
"""

import os
import re
import json
import argparse
from typing import Optional, Dict


# ============================================================
# LLM 解析层
# ============================================================

PARSE_PROMPT = """把中文数学问题转成 JSON。

【谓词】
prime(p), composite(n), even(n), odd(n), divides(a,b), coprime(a,b),
congruent(a,b,m), equals(a,b), irrational(x), quadratic_residue(a,p),
legendre_symbol(a,p), primitive_root(g,n), pythagorean(a,b,c),
sum_to_n(n,S), prime_infinite, exists(x,P(x)), and(P1,P2), or(P1,P2),
integer(x), factorial(n), binomial(n,k), product_range(m,n)

【谓词参数顺序】（严格遵循，不要反）
- divides(a, b)：a 整除 b。a 是除数，b 是被除数。
  正确：3 整除 6 → divides(3, 6)
  正确：n! 整除 X → divides(factorial(n), X)
  错误：divides(X, factorial(n))   ← 反了！
- congruent(a, b, m)：a ≡ b (mod m)
  正确：7 ≡ 2 (mod 5) → congruent(7, 2, 5)
- equals(a, b)：a = b（对称，无所谓顺序）
- minus(a, b)：a - b（注意是 a 减 b）
- div(a, b)：a / b（a 是被除数，b 是除数）

【数学函数规范】（严格遵守）
- 平方根：统一写 sqrt(x)
  ✓ sqrt(5)
  ✗ power(5, div(1, 2))
  ✗ 5^(1/2)
- 幂：写 power(x, n)
- 不要使用 not(...) 谓词 —— 系统不支持否定
- 无理数只用 irrational(x)，不要展开定义
- 有理数只用 rational(x)，不要展开定义
- 互质只用 coprime(a, b)，不要展开定义
- 整除只用 divides(a, b)，不要展开定义

【重要约束】
- 如果目标命题需要"新定理"，新定理里**只能用**上面【谓词】段列出的谓词
- 不允许发明新谓词（如 not、rational、coprime 等，除非在【谓词】段里已有）
- 新定理的 body 里**不允许**出现 not(...)

【函数】
sqrt(x), power(a,n), plus(a,b), minus(a,b), times(a,b), gcd(a,b), phi(n), tau(n)

【策略】
direct=默认, contradiction=无穷多/不存在, induction=对所有n

【new_theorems 字段说明】
如果目标命题需要"人类已证的中间定理"才能证出，
把这些中间定理放进 new_theorems 数组。
每条定理的格式必须是：
{
  "id": "T_XXX",           ← 唯一 id，如 T_PROD_RANGE_EQ
  "name": "中文名",
  "head": "谓词(...)",     ← 结论
  "body": ["谓词1(...)", "谓词2(...)"],  ← 前提（空数组=公理）
  "category": "分类"
}

如果目标能直接用已有定理证明，new_theorems 写 []。

【输出格式】
{
  "goal": "<目标谓词>",
  "strategy": "direct|contradiction|induction",
  "var": null,
  "premises": [],
  "explanation": "<一句话说明>",
  "new_theorems": []
}

【示例 1】
输入：证明素数无穷多
输出：{"goal":"prime_infinite","strategy":"contradiction","var":null,"premises":[],"explanation":"素数无穷多","new_theorems":[]}

【示例 2】
输入：连续 n 个正整数乘积能被 n! 整除
输出：{
  "goal": "divides(factorial(n), product_range(m, n))",
  "strategy": "direct",
  "var": null,
  "premises": [],
  "explanation": "连续乘积 = n! · C(m+n-1, n)",
  "new_theorems": [
    {"id":"T_BINOM_INT","name":"组合数整性","head":"integer(binomial(n, k))","body":[],"category":"组合数"},
    {"id":"T_PROD_RANGE_EQ","name":"连续乘积公式","head":"equals(product_range(m, n), times(factorial(n), binomial(plus(m, minus(n, 1)), n)))","body":[],"category":"组合数"},
    {"id":"T_MUL_DIVIDES","name":"整数乘积整除性","head":"divides(a, times(a, c))","body":["integer(a)","integer(c)"],"category":"基础"},
    {"id":"T_FACT_INT","name":"阶乘整性","head":"integer(factorial(n))","body":[],"category":"基础"},
    {"id":"T_EQUAL_SUBST","name":"等量代换","head":"divides(a, c)","body":["equals(c, times(a, d))","divides(a, times(a, d))"],"category":"基础"}
  ]
}

【约束】
- exists 格式：exists(变量名, 谓词)
- and 格式：and(谓词1, 谓词2)
- 只输出 JSON，不要其他内容

注意：生成的定理必须严格遵循 Horn 子句格式，body 里不能包含 not, exists, and 等连接词。

你是一个数论定理证明助手。请将问题转换为 Horn 子句格式。
注意：
1. 不要尝试定义“无理数”、“有理数”等基础概念。
2. 如果系统里可能已有现成的定理（如 T018_POW, prime(5)），请直接作为 premises 给出。
3. 不要在 body 里使用 not, exists, and 等连接词。

【极其重要】你是一个“形式化翻译器”，而不是“解题器”。
无论用户输入的数学符号是“根号”、“√”还是“sqrt”，只要是你认识的数学运算，请一律转为标准的函数形式（如 sqrt(5)），绝不可以在 new_theorems 里生成任何“定义类”或“推导类”的定理！如果不需要新定理，必须严格返回 "new_theorems": []。

输入：{query}
输出："""


def parse_with_local_llm(query: str,
                         base_url: str = "http://127.0.0.1:8080/v1",
                         model: str = "qwen3-4b") -> Optional[Dict]:
    """用本地 llama.cpp server 解析自然语言"""
    import urllib.request
    import urllib.error

    prompt = PARSE_PROMPT.replace("{query}", query)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一个数学问题的形式化解析器。只输出 JSON，不要其他内容。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 1500,
        "chat_template_kwargs": {"enable_thinking": False},  # 关闭思考
        "stream": False,
    }

    try:
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(payload).encode('utf-8'),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        text = data["choices"][0]["message"]["content"]
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        text = data["choices"][0]["message"]["content"]
        
        # === 调试：打印原始输出 ===
        print(f"  [LLM 原始输出]: {text[:500]}")
        # ========================
        

        return _extract_json(text)
    except Exception as e:
        print(f"[本地 LLM 错误] {e}")
        return None


def _extract_json(text: str) -> Optional[Dict]:
    text = text.strip()
    
    # 去掉 markdown
    if "```" in text:
        m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if m:
            text = m.group(1).strip()
    
    # 直接尝试
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # 找 { ... }
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    
    # 尝试补全被截断的 JSON
    if text.startswith('{') and not text.endswith('}'):
        # 补全 premises 和 explanation
        if '"premises":' in text and '"premises":[' not in text:
            text = text.rstrip(',') + ', "premises": [], "explanation": ""}'
        elif text.endswith(','):
            text = text[:-1] + '}'
        else:
            text = text + '}'
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    
    return None


# ============================================================
# 规则解析层（无 API 时的 fallback）
# ============================================================

RULES = [
    # 无理数
    (r'根号\s*(\d+).*无理', lambda m: {"goal": f"irrational(sqrt({m.group(1)}))",
                                       "strategy": "direct",
                                       "explanation": f"证明 √{m.group(1)} 是无理数"}),
    # 素数
    (r'(\d+).*是素数', lambda m: {"goal": f"prime({m.group(1)})",
                                   "strategy": "direct",
                                   "explanation": f"证明 {m.group(1)} 是素数"}),
    # 素数无穷多
    (r'素数.*无穷|无穷.*素数', lambda m: {"goal": "prime_infinite",
                                      "strategy": "direct",   # ★ 改 direct
                                      "explanation": "证明素数无穷多"}),
    # 同余
    (r'(\d+).*同余.*(\d+).*模\s*(\d+)',
     lambda m: {"goal": f"congruent({m.group(1)}, {m.group(2)}, {m.group(3)})",
                "strategy": "direct",
                "explanation": f"验证 {m.group(1)} ≡ {m.group(2)} (mod {m.group(3)})"}),
    # 整除
    (r'(\d+).*整除\s*(\d+)', lambda m: {"goal": f"divides({m.group(1)}, {m.group(2)})",
                                         "strategy": "direct",
                                         "explanation": f"验证 {m.group(1)} 整除 {m.group(2)}"}),
    # 勾股
    (r'勾股.*(\d+).*(\d+).*(\d+)',
     lambda m: {"goal": f"pythagorean({m.group(1)}, {m.group(2)}, {m.group(3)})",
                "strategy": "direct",
                "explanation": f"验证 ({m.group(1)}, {m.group(2)}, {m.group(3)}) 是勾股三元组"}),
    # 欧拉函数
    (r'欧拉函数.*(\d+).*等于\s*(\d+)',
     lambda m: {"goal": f"equals(phi({m.group(1)}), {m.group(2)})",
                "strategy": "direct",
                "explanation": f"验证 φ({m.group(1)}) = {m.group(2)}"}),
    # 前 n 项和（归纳）
    (r'前\s*(\w+).*和|1.*到.*(\w+).*和',
     lambda m: {"goal": "sum_to_n(k, S)",
                "strategy": "induction",
                "var": "k",
                "explanation": "证明前 k 项和"}),
    # 奇数 = 两偶数之和加1
    (r'奇数.*两个偶数.*加\s*1|奇数.*偶数之和.*加\s*1',
     lambda m: {"goal": "exists(ab,and(even(a),and(even(b),equals(plus(plus(a,b),1),n))))",
                "strategy": "direct",
                "premises": ["odd(n)"],
                "explanation": "奇数=两偶数之和加1"}),
    
    # 偶数 = 两奇数之和
    (r'偶数.*两个奇数|偶数.*奇数之和',
     lambda m: {"goal": "exists(ab,and(odd(a),and(odd(b),equals(plus(a,b),n))))",
                "strategy": "direct",
                "premises": ["even(n)"],
                "explanation": "偶数=两奇数之和"}),
    # 任意奇数之和
    (r'(\d+)\s*个奇数.*和|(\d+)\s*个奇数.*之和',
     lambda m: {
         "goal": ...,  # 根据数量生成嵌套
         "strategy": "direct",
         "premises": ["odd(a)", "odd(b)", ...],
         "explanation": "..."
     }),
]


def parse_with_rules(query: str) -> Optional[Dict]:
    """规则解析（无 LLM 时的 fallback）"""
    for pattern, extractor in RULES:
        m = re.search(pattern, query)
        if m:
            return extractor(m)
    return None


# ============================================================
# 统一入口
# ============================================================

def parse_query(query: str, use_llm: bool = True,
                backend: str = "local",
                base_url: str = "http://127.0.0.1:8080/v1",
                model: str = "qwen3-4b") -> Optional[Dict]:
    """解析用户查询"""
    # 1. 先试规则（最快）
    result = parse_with_rules(query)
    if result:
        print(f"  [规则解析] 成功")
        return result

    # 2. 再试本地 LLM
    if use_llm:
        if backend == "local":
            print(f"  [本地 LLM] 调用 {base_url} ...")
            result = parse_with_local_llm(query, base_url, model)
        else:
            print(f"  [API] 调用 {backend} ...")
            result = parse_with_local_llm(query, backend)

        if result:
            print(f"  [LLM 解析] 成功")
            return result

    print(f"  [解析失败] 无法理解: {query}")
    return None


# ============================================================
# 主流程
# ============================================================

def prove_query(query: str, use_llm: bool = True,
                backend: str = "local",
                base_url: str = "http://127.0.0.1:8080/v1",
                model: str = "qwen3-4b",
                verbose: bool = True):
    """完整流程：中文 → 证明"""
    print(f"\n{'='*60}")
    print(f"用户输入: {query}")
    print('='*60)

    # 1. 解析
    parsed = parse_query(query, use_llm, backend, base_url, model)
    if not parsed:
        return None

    goal = parsed.get("goal")
    strategy = parsed.get("strategy", "auto")
    var = parsed.get("var")
    explanation = parsed.get("explanation", "")

    print(f"  目标: {goal}")
    print(f"  策略: {strategy}")
    if var:
        print(f"  变量: {var}")
    if explanation:
        print(f"  说明: {explanation}")

    # 2. 调用证明器
    from numtheory_prover import build_theorem_db, Prover, parse_goal, Var, print_proof
    from adaptive_store import AdaptiveStore
    from adaptive_prover import AdaptiveProver

    store = AdaptiveStore()
    store.load_jsonl('theorems.jsonl')
    import glob
    for path in sorted(glob.glob('theorems/*.jsonl')):
        store.load_jsonl(path)
    store.load_weights()

    ap = AdaptiveProver(store, max_rounds=3, base_top_k=20)
    var_obj = Var(var) if var else None

    premises = parsed.get("premises", [])
    premise_objs = [parse_goal(p) for p in premises] if premises else []
    premise_objs = [p for p in premise_objs if p is not None]

    if premise_objs:
        # 用底层 Prover 支持前提
        from numtheory_prover import Prover, build_theorem_db
        db = list(store.clauses)
        prover2 = Prover(db, max_depth=12)
        proof = prover2.prove_with_premises(
            parse_goal(goal), premise_objs,
            strategy=strategy, var=var_obj, verbose=False
        )
    else:
        proof = ap.prove(goal, strategy=strategy, var=var_obj, verbose=False)


    # 如果失败且策略不是 direct，尝试 direct
    if proof is None and strategy != "direct":
        print(f"  [{strategy} 失败，尝试 direct...]")
        proof = ap.prove(goal, strategy="direct", var=None, verbose=False)

    # 如果还是失败，尝试所有策略
    if proof is None:
        for alt_strategy in ["auto", "direct", "contradiction"]:
            if alt_strategy == strategy:
                continue
            print(f"  [尝试 {alt_strategy}...]")
            proof = ap.prove(goal, strategy=alt_strategy, var=var_obj, verbose=False)
            if proof:
                break
    # 3. 输出
    if proof:
        print(f"\n  ✅ 证明成功")
        print_proof(proof, parse_goal(goal))
        return proof
    else:
        print(f"\n  ❌ 未能证明")
        return None


def interactive():
    """交互模式"""
    print("=" * 60)
    print("数论定理证明器 · 自然语言接口")
    print("=" * 60)
    print("示例：")
    print("  证明根号2是无理数")
    print("  7是素数吗")
    print("  证明素数无穷多")
    print("  验证 7 同余于 2 模 5")
    print("  3 整除 6 吗")
    print("  欧拉函数10等于4")
    print("  输入 q 退出")
    print()

    while True:
        try:
            query = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if query.lower() in ('q', 'quit', 'exit'):
            break
        if not query:
            continue
        prove_query(query)


def cli():
    parser = argparse.ArgumentParser(description="自然语言证明接口")
    parser.add_argument('--query', type=str, help='自然语言查询')
    parser.add_argument('--interactive', action='store_true', help='交互模式')
    parser.add_argument('--no_llm', action='store_true', help='禁用 LLM（只用规则）')
    parser.add_argument('--backend', choices=['local', 'deepseek', 'qwen', 'openai'],
                        default='local', help='LLM 后端')
    parser.add_argument('--base_url', type=str,
                        default='http://127.0.0.1:8080/v1',
                        help='llama.cpp server 地址')
    parser.add_argument('--model', type=str, default='qwen3-4b',
                        help='模型名称')
    args = parser.parse_args()

    if args.interactive:
        interactive()
        return

    if args.query:
        prove_query(args.query,
            use_llm=not args.no_llm,
            backend=args.backend,
            base_url=args.base_url,
            model=args.model)
        return

    parser.print_help()


if __name__ == "__main__":
    cli()