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
sum_to_n(n,S), prime_infinite, exists(x,P(x)), and(P1,P2), or(P1,P2)

【函数】
sqrt(x), power(a,n), plus(a,b), minus(a,b), times(a,b), gcd(a,b), phi(n), tau(n)

【策略】
direct=默认, contradiction=无穷多/不存在, induction=对所有n

【示例】
输入：证明任意奇数可以表示为两个偶数之和加1
输出：{"goal":"exists(ab,and(even(a),and(even(b),equals(plus(plus(a,b),1),n))))","strategy":"direct","var":null,"premises":["odd(n)"],"explanation":"奇数=两偶数之和加1"}

输入：证明根号2是无理数
输出：{"goal":"irrational(sqrt(2))","strategy":"direct","var":null,"premises":[],"explanation":"证明√2无理"}

输入：证明素数无穷多
输出：{"goal":"prime_infinite","strategy":"contradiction","var":null,"premises":[],"explanation":"素数无穷多"}

输入：证明任意偶数可以表示为两个奇数之和
输出：{"goal":"exists(ab,and(odd(a),and(odd(b),equals(plus(a,b),n))))","strategy":"direct","var":null,"premises":["even(n)"],"explanation":"偶数=两奇数之和"}

【输出格式约束】
- exists 的格式是 exists(变量名, 谓词)，例如 exists(ab, and(...))
- and 的格式是 and(谓词1, 谓词2)
- 不要引入多余的变量
- 严格参照示例的格式

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
                                          "strategy": "contradiction",
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