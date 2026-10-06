# -*- coding: utf-8 -*-
"""
Created on Tue Oct  6 11:13:57 2026

@author: gzche
"""

"""
把 build_theorem_db() 的结果导出为 theorems.jsonl
"""
import json
from numtheory_prover import build_theorem_db


def clause_to_dict(c):
    """HornClause → dict"""
    def term_to_str(t):
        return str(t)
    
    return {
        "id": c.id,
        "name": c.name,
        "category": c.category,
        "head": term_to_str(c.head),
        "body": [term_to_str(b) for b in c.body],
        "keywords": extract_keywords(c),
    }


def extract_keywords(c):
    """从 name + category + head + body 里抽关键词"""
    kws = set()
    # name 里的 2-4 字词
    for m in re.findall(r'[\u4e00-\u9fff]{2,4}', c.name):
        kws.add(m)
    kws.add(c.category)
    # head/body 里的谓词
    kws.add(c.head.name)
    for b in c.body:
        kws.add(b.name)
    return sorted(kws)


if __name__ == "__main__":
    import re
    db = build_theorem_db()
    with open("theorems.jsonl", "w", encoding="utf-8") as f:
        for c in db:
            obj = clause_to_dict(c)
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    print(f"导出 {len(db)} 条定理到 theorems.jsonl")