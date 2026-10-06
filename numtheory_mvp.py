"""
数论版全互联网络 MVP（L1-L4，不含证明链）

设计：
  L1 符号层     数学符号识别（|、≡、gcd、prime、phi、tau……）
  L2 概念层     数论术语识别（素数、整除、同余、互质……）
  L3 定理层     从自然语言定理抽三元组 (前提, 关系, 结论)
  L4 检索层     给定条件，返回匹配定理

用法：
  python numtheory_mvp.py --build                 # 建库
  python numtheory_mvp.py --query "素数 整除 乘积"  # 查询
  python numtheory_mvp.py --demo                  # 演示
  python numtheory_mvp.py --interactive           # 交互
"""

import os
import re
import json
import pickle
import random
import argparse
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional


# ============================================================
# L1：符号层
# ============================================================

# 数学符号 → 标准形式
SYMBOL_MAP = {
    "|": "divides",
    "∤": "not_divides",
    "≡": "congruent",
    "≠": "not_equals",
    "≥": "ge",
    "≤": "le",
    "∈": "in",
    "∀": "forall",
    "∃": "exists",
    "√": "sqrt",
    "·": "*",
    "×": "*",
}

# 数论专有名词（英文 → 中文）
TERM_MAP = {
    "prime": "素数",
    "composite": "合数",
    "divides": "整除",
    "divisor": "约数",
    "multiple": "倍数",
    "gcd": "最大公约数",
    "lcm": "最小公倍数",
    "coprime": "互质",
    "congruent": "同余",
    "mod": "模",
    "phi": "欧拉函数",
    "tau": "约数个数",
    "sigma": "约数和",
    "factorial": "阶乘",
    "perfect": "完全数",
    "pythagorean": "勾股",
    "diophantine": "丢番图",
    "pell": "佩尔",
    "fermat": "费马",
    "euler": "欧拉",
    "wilson": "威尔逊",
    "euclid": "欧几里得",
    "infinite": "无穷",
    "asymptotic": "渐近",
}


def normalize_symbols(text: str) -> str:
    """把数学符号统一成规范形式"""
    for sym, std in SYMBOL_MAP.items():
        text = text.replace(sym, f" {std} ")
    return text


def normalize_terms(text: str) -> str:
    """把英文数论术语替换成中文"""
    for en, cn in TERM_MAP.items():
        text = re.sub(r'\b' + en + r'\b', cn, text, flags=re.IGNORECASE)
    return text


# ============================================================
# L2：概念层
# ============================================================

@dataclass
class Concept:
    name: str
    aliases: List[str]
    category: str  # 数系 / 性质 / 关系 / 函数

    def matches(self, text: str) -> bool:
        return any(a in text for a in self.aliases)


CONCEPTS = [
    # 数系
    Concept("自然数", ["自然数", "正整数"], "数系"),
    Concept("整数", ["整数"], "数系"),
    Concept("有理数", ["有理数"], "数系"),
    Concept("无理数", ["无理数"], "数系"),
    # 数的性质
    Concept("素数", ["素数", "质数"], "性质"),
    Concept("合数", ["合数"], "性质"),
    Concept("奇数", ["奇数"], "性质"),
    Concept("偶数", ["偶数"], "性质"),
    Concept("完全数", ["完全数"], "性质"),
    Concept("完全平方数", ["完全平方数", "平方数"], "性质"),
    # 关系
    Concept("整除", ["整除", "divides"], "关系"),
    Concept("互质", ["互质", "coprime"], "关系"),
    Concept("同余", ["同余", "congruent"], "关系"),
    Concept("等于", ["等于", "equals"], "关系"),
    Concept("大于", ["大于", "gt"], "关系"),
    Concept("小于", ["小于", "lt"], "关系"),
    # 函数
    Concept("最大公约数", ["最大公约数", "gcd"], "函数"),
    Concept("最小公倍数", ["最小公倍数", "lcm"], "函数"),
    Concept("欧拉函数", ["欧拉函数", "phi"], "函数"),
    Concept("约数个数", ["约数个数", "tau"], "函数"),
    Concept("约数和", ["约数和", "sigma"], "函数"),
    Concept("阶乘", ["阶乘", "factorial"], "函数"),
    # 定理名
    Concept("费马小定理", ["费马小定理", "费马"], "定理"),
    Concept("欧拉定理", ["欧拉定理"], "定理"),
    Concept("威尔逊定理", ["威尔逊定理", "威尔逊"], "定理"),
    Concept("中国剩余定理", ["中国剩余定理", "中国剩余"], "定理"),
    Concept("贝祖等式", ["贝祖等式", "贝祖"], "定理"),
    Concept("欧几里得引理", ["欧几里得引理", "欧几里得"], "定理"),
    Concept("算术基本定理", ["算术基本定理", "唯一分解"], "定理"),
    Concept("勾股定理", ["勾股定理", "勾股"], "定理"),
]


class ConceptLayer:
    """L2：概念识别"""

    def __init__(self):
        self.concepts = CONCEPTS
        self.by_name = {c.name: c for c in CONCEPTS}
        # 别名 → 标准名
        self.alias_to_name = {}
        for c in CONCEPTS:
            for a in c.aliases:
                self.alias_to_name[a] = c.name

    def extract_concepts(self, text: str) -> Set[str]:
        """从文本中抽出所有概念（返回标准名）"""
        found = set()
        for c in self.concepts:
            if c.matches(text):
                found.add(c.name)
        return found

    def concept_of(self, text: str) -> Optional[str]:
        """返回文本里最长的概念（标准名）"""
        best = None
        best_len = 0
        for c in self.concepts:
            for a in c.aliases:
                if a in text and len(a) > best_len:
                    best = c.name
                    best_len = len(a)
        return best


# ============================================================
# L3：定理层
# ============================================================

@dataclass
class Theorem:
    id: str
    name: str
    category: str
    premises: List[str]          # 前提条件（概念列表）
    conclusion: str              # 结论（概念）
    raw_text: str                # 原始文本
    concepts: Set[str] = field(default_factory=set)
    examples: List[str] = field(default_factory=list)
    proof: str = ""

    def signature(self) -> str:
        """定理的"指纹"：用于去重"""
        return f"{self.name}|{self.conclusion}"

    def matches_query(self, query_concepts: Set[str]) -> float:
        """定理与查询的匹配度（0-1）"""
        if not query_concepts:
            return 0.0
        overlap = self.concepts & query_concepts
        if not overlap:
            return 0.0
        # Jaccard + 前提命中加权
        jaccard = len(overlap) / len(self.concepts | query_concepts)
        premise_bonus = 0.0
        for c in query_concepts:
            if c in self.premises:
                premise_bonus += 0.3
        return jaccard + premise_bonus


class TheoremLayer:
    """L3：定理抽取与存储"""

    def __init__(self, concept_layer: ConceptLayer):
        self.concept_layer = concept_layer
        self.theorems: List[Theorem] = []
        self.seen_signatures: Set[str] = set()

    def add_theorem(self, t: Theorem):
        sig = t.signature()
        if sig in self.seen_signatures:
            return False
        self.seen_signatures.add(sig)
        self.theorems.append(t)
        return True

    def build_from_jsonl(self, path: str):
        """从 numtheory_sft.jsonl 或原始 JSONL 建库"""
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # 支持两种格式：
                # 1) SFT 格式：{"text": "..."}
                # 2) 原始格式：{"id":..., "name":..., "pre":..., "con":...}
                if "text" in obj:
                    self._add_from_text(obj["text"])
                elif "name" in obj and "con" in obj:
                    self._add_from_structured(obj)

    def _add_from_text(self, text: str):
        """从自然语言文本解析定理"""
        text = normalize_symbols(text)
        text = normalize_terms(text)

        # 抽【类别】名字
        cat_match = re.match(r'【(.+?)】(.+?)。', text)
        if cat_match:
            category = cat_match.group(1)
            name = cat_match.group(2)
        else:
            category = "未分类"
            # 取第一个句号前的部分
            m = re.match(r'(.+?)。', text)
            name = m.group(1) if m else text[:20]

        # 抽前提（"若...则..."）
        premises = []
        conclusion = ""
        m = re.search(r'若(.+?)，则(.+?)。', text)
        if m:
            prem_text = m.group(1)
            con_text = m.group(2)
            premises = self._extract_premises(prem_text)
            conclusion = self.concept_layer.concept_of(con_text) or con_text[:10]
        else:
            # 没有"若...则..."，整句当结论
            m2 = re.search(r'。([^。]+)。', text)
            if m2:
                conclusion = self.concept_layer.concept_of(m2.group(1)) or ""

        # 抽例子
        examples = re.findall(r'例子：(.+?)。', text)

        # 抽证明方法
        proof_match = re.search(r'证明方法：(.+?)。', text)
        proof = proof_match.group(1) if proof_match else ""

        # 抽所有概念
        concepts = self.concept_layer.extract_concepts(text)

        t = Theorem(
            id=f"T{len(self.theorems)+1:04d}",
            name=name,
            category=category,
            premises=premises,
            conclusion=conclusion,
            raw_text=text,
            concepts=concepts,
            examples=examples,
            proof=proof,
        )
        self.add_theorem(t)

    def _extract_premises(self, prem_text: str) -> List[str]:
        """从前提文本里抽概念列表"""
        concepts = self.concept_layer.extract_concepts(prem_text)
        return list(concepts)

    def _add_from_structured(self, obj: Dict):
        """从结构化 JSON 解析（备用）"""
        # 兼容老格式
        pass

    def retrieve(self, query: str, top_k: int = 5) -> List[Tuple[Theorem, float]]:
        """检索匹配的定理"""
        query = normalize_symbols(query)
        query = normalize_terms(query)
        query_concepts = self.concept_layer.extract_concepts(query)
        if not query_concepts:
            # 没有识别到概念，退回关键词匹配
            return self._keyword_match(query, top_k)

        scored = []
        for t in self.theorems:
            score = t.matches_query(query_concepts)
            if score > 0:
                scored.append((t, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _keyword_match(self, query: str, top_k: int) -> List[Tuple[Theorem, float]]:
        """关键词匹配（备用）"""
        scored = []
        keywords = re.findall(r'[\u4e00-\u9fff]{2,}', query)
        for t in self.theorems:
            score = 0.0
            for kw in keywords:
                if kw in t.raw_text:
                    score += 1.0
            if score > 0:
                scored.append((t, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def stats(self) -> Dict:
        by_cat = Counter(t.category for t in self.theorems)
        return {
            '定理总数': len(self.theorems),
            '按类别': dict(by_cat),
            '唯一概念数': len(set().union(*[t.concepts for t in self.theorems]) if self.theorems else set()),
        }


# ============================================================
# L4：检索层
# ============================================================

class RetrievalLayer:
    """L4：组合检索 + 排序"""

    def __init__(self, theorem_layer: TheoremLayer,
                 concept_layer: ConceptLayer):
        self.theorems = theorem_layer
        self.concepts = concept_layer

    def search(self, query: str, top_k: int = 5,
               verbose: bool = True) -> List[Theorem]:
        """主检索入口"""
        if verbose:
            print(f"\n查询: 「{query}」")

        # 1. 概念识别
        query_norm = normalize_terms(normalize_symbols(query))
        query_concepts = self.concepts.extract_concepts(query_norm)

        if verbose:
            print(f"识别概念: {sorted(query_concepts) if query_concepts else '（无）'}")

        # 2. 检索
        results = self.theorems.retrieve(query, top_k=top_k)

        if verbose:
            print(f"命中 {len(results)} 条定理")
            print("-" * 60)

        return [t for t, _ in results]


# ============================================================
# 内置默认语料（若没有 numtheory_sft.jsonl）
# ============================================================

DEFAULT_CORPUS = [
    {"text": "【整除理论】整除的传递性。若a整除b，且b整除c，则a整除c。例子：2整除6，6整除18，所以2整除18。"},
    {"text": "【整除理论】整除的自反性。任何整数都整除自己。例子：5整除5。"},
    {"text": "【整除理论】整除的线性组合。若a整除b，且a整除c，则a整除mb加nc。例子：2整除6，2整除10。"},
    {"text": "【整除理论】1整除一切。1整除任何整数。例子：1整除7。"},
    {"text": "【整除理论】一切整除0。任何整数都整除0。例子：3整除0。"},
    {"text": "【素数理论】素数定义。若p大于1，且p只有1和它本身两个约数，则p是素数。例子：2是素数。"},
    {"text": "【素数理论】素数无穷多。对任意正整数n，存在素数p大于n。证明方法：反证法。"},
    {"text": "【素数理论】欧几里得引理。若p是素数，且p整除a乘以b，则p整除a或p整除b。例子：2整除12，则2整除4。"},
    {"text": "【素数理论】算术基本定理。任何大于1的整数都有唯一的素数分解。例子：12等于2的平方乘以3。"},
    {"text": "【素数理论】费马小定理。若p是素数，且a与p互质，则a的p减1次方同余于1模p。例子：3的6次方同余于1模7。"},
    {"text": "【素数理论】威尔逊定理。p是素数当且仅当p减1的阶乘同余于负1模p。例子：5的阶乘等于24，同余于负1模5。"},
    {"text": "【同余理论】同余定义。a同余于b模m当且仅当m整除a减b。例子：7同余于2模5。"},
    {"text": "【同余理论】同余的加法。若a同余于b模m，且c同余于d模m，则a加c同余于b加d模m。"},
    {"text": "【同余理论】同余的乘法。若a同余于b模m，且c同余于d模m，则ac同余于bd模m。"},
    {"text": "【同余理论】中国剩余定理。若m1和m2互质，则同余方程组有唯一解。例子：x同余于2模3，x同余于3模5，则x等于8。"},
    {"text": "【同余理论】欧拉定理。若a与n互质，则a的欧拉函数n次方同余于1模n。例子：3的4次方同余于1模10。"},
    {"text": "【最大公约数理论】欧几里得算法。gcd(a,b)等于gcd(b, a模b)。例子：gcd(48,18)等于6。"},
    {"text": "【最大公约数理论】贝祖等式。存在整数x和y，使得ax加by等于gcd(a,b)。例子：12乘1加8乘负1等于4。"},
    {"text": "【最大公约数理论】gcd与lcm关系。gcd(a,b)乘lcm(a,b)等于a乘b。例子：gcd(4,6)乘lcm(4,6)等于24。"},
    {"text": "【最大公约数理论】互质与整除。若a与b互质，且a整除bc，则a整除c。例子：3与5互质，3整除15，则3整除15。"},
    {"text": "【算术函数理论】欧拉函数定义。欧拉函数n等于小于n且与n互质的正整数个数。例子：欧拉函数10等于4。"},
    {"text": "【算术函数理论】欧拉函数的积性。若m与n互质，则欧拉函数mn等于欧拉函数m乘欧拉函数n。例子：欧拉函数15等于8。"},
    {"text": "【算术函数理论】约数个数。n的约数个数等于各素数指数加1的乘积。例子：12等于2的平方乘3，约数个数等于6。"},
    {"text": "【算术函数理论】约数和。n的约数和等于各素数幂和的乘积。例子：6的约数和等于12。"},
    {"text": "【丢番图方程】线性丢番图方程。ax加by等于c有整数解当且仅当gcd(a,b)整除c。例子：3x加5y等于1有解。"},
    {"text": "【丢番图方程】本原勾股三元组。a方加b方等于c方，且a、b、c两两互质，则存在m大于n，gcd(m,n)等于1，a等于m方减n方，b等于2mn，c等于m方加n方。例子：3、4、5。"},
    {"text": "【丢番图方程】四平方和定理。任何非负整数都可以表示为四个平方数之和。例子：7等于4加1加1加1。"},
]


# ============================================================
# 主程序
# ============================================================

CACHE_FILE = "numtheory_mvp_cache.pkl"


def build(data_path: str = None, use_default: bool = False,
          cache: str = CACHE_FILE, verbose: bool = True):
    """建库"""
    if os.path.exists(cache):
        if verbose:
            print(f"[*] 从缓存加载: {cache}")
        with open(cache, 'rb') as f:
            data = pickle.load(f)
        return data['concept_layer'], data['theorem_layer']

    if verbose:
        print("[1] 构建 L2 概念层...")
    concept_layer = ConceptLayer()
    if verbose:
        print(f"  {len(concept_layer.concepts)} 个概念")

    if verbose:
        print("[2] 构建 L3 定理层...")
    theorem_layer = TheoremLayer(concept_layer)

    if use_default or not data_path or not os.path.exists(data_path):
        if verbose:
            print(f"  使用内置语料（{len(DEFAULT_CORPUS)} 条）")
        for obj in DEFAULT_CORPUS:
            theorem_layer._add_from_text(obj['text'])
    else:
        if verbose:
            print(f"  从 {data_path} 加载")
        theorem_layer.build_from_jsonl(data_path)

    if verbose:
        stats = theorem_layer.stats()
        print(f"  定理总数: {stats['定理总数']}")
        print(f"  按类别: {stats['按类别']}")
        print(f"  唯一概念: {stats['唯一概念数']}")

    # 缓存
    with open(cache, 'wb') as f:
        pickle.dump({
            'concept_layer': concept_layer,
            'theorem_layer': theorem_layer,
        }, f)
    if verbose:
        size = os.path.getsize(cache) / 1024
        print(f"[3] 已缓存到 {cache} ({size:.1f} KB)")

    return concept_layer, theorem_layer


def print_results(theorems: List[Theorem], verbose: bool = True):
    """打印检索结果"""
    if not theorems:
        print("  （无匹配）")
        return
    for i, t in enumerate(theorems, 1):
        print(f"\n[{i}] {t.name}  （{t.category}）")
        print(f"    前提: {t.premises if t.premises else '（无）'}")
        print(f"    结论: {t.conclusion}")
        if t.examples:
            print(f"    例子: {t.examples[0]}")
        if verbose:
            print(f"    原文: {t.raw_text[:100]}...")


def run_demo(concept_layer, theorem_layer):
    """演示"""
    retrieval = RetrievalLayer(theorem_layer, concept_layer)

    queries = [
        "素数 整除 乘积",
        "gcd 线性组合",
        "同余 加法 乘法",
        "费马小定理",
        "勾股 参数化",
        "欧拉函数",
        "中国剩余定理",
        "四平方和",
    ]

    for q in queries:
        print("\n" + "=" * 60)
        results = retrieval.search(q, top_k=3)
        print_results(results)


def interactive(concept_layer, theorem_layer):
    """交互模式"""
    retrieval = RetrievalLayer(theorem_layer, concept_layer)
    print("\n" + "=" * 60)
    print("数论定理检索 · 交互模式")
    print("=" * 60)
    print("输入查询（如：素数 整除 乘积），q 退出")
    while True:
        try:
            q = input("\n>>> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in ('q', 'quit', 'exit'):
            break
        if not q:
            continue
        results = retrieval.search(q, top_k=5)
        print_results(results)


def cli():
    parser = argparse.ArgumentParser(
        description="数论版全互联网络 MVP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python numtheory_mvp.py --build                  # 建库（内置语料）
  python numtheory_mvp.py --build --data numtheory_sft.jsonl
  python numtheory_mvp.py --demo                   # 演示
  python numtheory_mvp.py --query "素数 整除 乘积"
  python numtheory_mvp.py --interactive
  python numtheory_mvp.py --no_cache --build       # 禁用缓存重建
        """,
    )
    parser.add_argument('--build', action='store_true', help='建库')
    parser.add_argument('--data', type=str, help='语料路径（JSONL）')
    parser.add_argument('--query', type=str, help='查询词')
    parser.add_argument('--demo', action='store_true', help='跑演示')
    parser.add_argument('--interactive', action='store_true', help='交互模式')
    parser.add_argument('--no_cache', action='store_true', help='禁用缓存')
    parser.add_argument('--top_k', type=int, default=3, help='返回条数')
    parser.add_argument('--stats', action='store_true', help='显示统计')
    parser.add_argument('--concepts', action='store_true', help='显示所有概念')
    args = parser.parse_args()

    print("=" * 60)
    print("数论版全互联网络 MVP")
    print("=" * 60)

    cache = "__no_cache__.pkl" if args.no_cache else CACHE_FILE

    # 建库
    if args.build or not os.path.exists(cache):
        concept_layer, theorem_layer = build(
            data_path=args.data,
            use_default=not args.data,
            cache=cache,
        )
    else:
        print(f"[*] 从缓存加载: {cache}")
        with open(cache, 'rb') as f:
            data = pickle.load(f)
        concept_layer = data['concept_layer']
        theorem_layer = data['theorem_layer']

    # 分发
    if args.concepts:
        print("\n[所有概念]")
        for c in concept_layer.concepts:
            print(f"  {c.name}  ({c.category})  别名: {c.aliases}")
        return

    if args.stats:
        print("\n[统计]")
        stats = theorem_layer.stats()
        print(f"  定理总数: {stats['定理总数']}")
        print(f"  按类别: {stats['按类别']}")
        print(f"  唯一概念: {stats['唯一概念数']}")
        return

    if args.query:
        retrieval = RetrievalLayer(theorem_layer, concept_layer)
        results = retrieval.search(args.query, top_k=args.top_k)
        print_results(results)
        return

    if args.demo:
        run_demo(concept_layer, theorem_layer)
        return

    if args.interactive:
        interactive(concept_layer, theorem_layer)
        return

    # 默认跑 demo
    run_demo(concept_layer, theorem_layer)


if __name__ == "__main__":
    cli()