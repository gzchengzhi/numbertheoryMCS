#!/usr/bin/env python3
"""
定理库去重与归类。

用法：
    python tools/dedup_theorems.py --scan                # 只扫描，输出报告
    python tools/dedup_theorems.py --apply               # 执行合并（写回 + 备份）
    python tools/dedup_theorems.py --scan --json out.json # 机器可读报告

设计：
- L1 字面重复：直接合并
- L2 α-等价（变量名不同）：按 canonical 变量序归一后合并
- L3 语义等价：只归组，不合并
- 任何写操作前自动备份到 .bak/
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import json
import glob
import os
import shutil
from datetime import datetime
from collections import defaultdict

from numtheory_prover import parse_goal, HornClause, Var, Const, Pred
from adaptive_store import AdaptiveStore


# ---------- 1. 变量归一化 ----------

def canonicalize_terms(pred: Pred) -> tuple:
    """
    把 Pred 里所有 Var 按首次出现顺序重命名为 v0, v1, ...
    返回 (pred_name, tuple(canonical_arg_str))。
    这样 divides(a,b) 与 divides(x,y) 得到同一个 signature。
    """
    var_map = {}
    counter = [0]

    def walk(t):
        tn = type(t).__name__
        if tn == "Var":
            if t.name not in var_map:
                var_map[t.name] = f"v{counter[0]}"
                counter[0] += 1
            return var_map[t.name]
        if tn == "Const":
            if not t.args:
                return f"C:{t.name}"
            return f"F:{t.name}(" + ",".join(walk(a) for a in t.args) + ")"
        if tn == "Pred":
            return f"P:{t.name}(" + ",".join(walk(a) for a in t.args) + ")"
        return str(t)

    return (pred.name, tuple(walk(a) for a in pred.args))


def clause_signature(clause: HornClause) -> tuple:
    """head + body 的 canonical signature（变量全归一）"""
    head_sig = canonicalize_terms(clause.head)
    body_sigs = tuple(sorted(canonicalize_terms(b) for b in clause.body))
    return (head_sig, body_sigs)


def literal_signature(clause: HornClause) -> tuple:
    """完全字面签名（含原始变量名），用于 L1 检测"""
    return (
        str(clause.head),
        tuple(sorted(str(b) for b in clause.body)),
        clause.category or "",
    )


# ---------- 2. 语义等价归组 ----------

def semantic_groups(clause: HornClause, rules) -> list:
    """
    对 clause 的 head 与每个 body，尝试匹配 SEMANTIC_EQUIV，
    返回命中的 group 名列表（去重）。
    """
    from numtheory_prover import unify

    hits = []
    preds = [clause.head] + list(clause.body)
    for pred in preds:
        for rule in rules:
            for side in ("left", "right"):
                pat_name, pat_args = rule[side]
                if pred.name != pat_name:
                    continue
                # 构造 pattern Pred（args 里可能含函数式字符串，简单处理）
                try:
                    pat_args_terms = tuple(
                        parse_goal(f"{pat_name}({','.join(pat_args)})").args
                        if isinstance(a, str) and "(" in a
                        else Var(a)
                        for a in pat_args
                    )
                    pattern = Pred(pat_name, pat_args_terms)
                except Exception:
                    continue
                if unify(pattern, pred, {}) is not None:
                    hits.append(rule["group"])
                    break
    return sorted(set(hits))


# ---------- 3. 主扫描 ----------

def load_all(dirs):
    store = AdaptiveStore()
    files = []
    for d in dirs:
        files.extend(sorted(glob.glob(os.path.join(d, "*.jsonl"))))
        files.extend(sorted(glob.glob(os.path.join(d, "**", "*.jsonl"), recursive=True)))
    files = sorted(set(files))
    for f in files:
        store.load_jsonl(f)
    return store, files


def scan(store, rules):
    """
    返回：
      {
        "L1": [ [id1, id2, ...], ... ],           # 字面重复组
        "L2": [ [id1, id2, ...], ... ],           # α-等价组
        "L3": {group: [id, ...]},                 # 语义组
        "stats": {...},
        "by_file": {file: [id, ...]},             # 每个 id 来自哪个文件（用于回写）
      }
    """
    l1_index = defaultdict(list)
    l2_index = defaultdict(list)
    l3_index = defaultdict(list)
    id_to_signature = {}
    id_to_file = {}

    # 先建立 id -> 来源文件（需要重新扫一遍文件，因为 store 不记来源）
    # 这里用一个轻量扫描
    # （如果你的 load_jsonl 有记录来源，直接读 store 即可）

    for c in store.clauses:
        cid = c.id
        lit_sig = literal_signature(c)
        can_sig = clause_signature(c)
        l1_index[lit_sig].append(cid)
        l2_index[can_sig].append(cid)
        id_to_signature[cid] = can_sig

        groups = semantic_groups(c, rules)
        for g in groups:
            l3_index[g].append(cid)

    l1_groups = [sorted(v) for v in l1_index.values() if len(v) > 1]
    l2_groups = [sorted(v) for v in l2_index.values() if len(v) > 1]
    # L2 里已经包含了 L1（字面重复必然 α-等价），从 L2 里剔除纯 L1 组
    l1_set = {tuple(g) for g in l1_groups}
    l2_groups = [g for g in l2_groups if tuple(g) not in l1_set]

    l3_groups = {g: sorted(v) for g, v in l3_index.items() if len(v) > 1}

    return {
        "L1": l1_groups,
        "L2": l2_groups,
        "L3": l3_groups,
        "stats": {
            "total": len(store.clauses),
            "L1_groups": len(l1_groups),
            "L1_removable": sum(len(g) - 1 for g in l1_groups),
            "L2_groups": len(l2_groups),
            "L2_removable": sum(len(g) - 1 for g in l2_groups),
            "L3_groups": len(l3_groups),
        },
        "by_file": id_to_file,
    }


# ---------- 4. 报告 ----------

def print_report(result, store):
    st = result["stats"]
    print("=" * 60)
    print("定理库去重扫描报告")
    print("=" * 60)
    print(f"总定理数:           {st['total']}")
    print(f"L1 字面重复组:      {st['L1_groups']:>3}  (可删 {st['L1_removable']} 条)")
    print(f"L2 α-等价组:       {st['L2_groups']:>3}  (可合并 {st['L2_removable']} 条)")
    print(f"L3 语义等价组:      {st['L3_groups']:>3}  (仅归类，不删)")
    print()

    if result["L1"]:
        print("--- L1 字面重复（建议直接删）---")
        for g in result["L1"][:20]:
            keep = g[0]
            drop = g[1:]
            c = store.by_id.get(keep)
            print(f"  保留 {keep}: {c.name if c else '?'}")
            print(f"    删除 {drop}")
        if len(result["L1"]) > 20:
            print(f"  ... 另有 {len(result['L1']) - 20} 组")
        print()

    if result["L2"]:
        print("--- L2 α-等价（变量名不同，建议合并）---")
        for g in result["L2"][:30]:
            keep = g[0]
            c = store.by_id.get(keep)
            print(f"  保留 {keep}: {str(c.head) if c else '?'}")
            for other in g[1:]:
                oc = store.by_id.get(other)
                print(f"    合并 {other}: {str(oc.head) if oc else '?'}")
        if len(result["L2"]) > 30:
            print(f"  ... 另有 {len(result['L2']) - 30} 组")
        print()

    if result["L3"]:
        print("--- L3 语义等价（只归类，人工确认）---")
        for group, ids in result["L3"].items():
            print(f"  [{group}] {len(ids)} 条:")
            for cid in ids[:8]:
                c = store.by_id.get(cid)
                print(f"    {cid}: {str(c.head) if c else '?'}")
            if len(ids) > 8:
                print(f"    ... 另有 {len(ids) - 8} 条")
        print()


# ---------- 5. 执行合并 ----------

def backup_files(files):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak_dir = f".bak/dedup_{ts}"
    os.makedirs(bak_dir, exist_ok=True)
    for f in files:
        if os.path.exists(f):
            rel = os.path.relpath(f)
            dst = os.path.join(bak_dir, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(f, dst)
    print(f"备份完成 → {bak_dir}/")
    return bak_dir


def apply_merge(result, store, files):
    """
    对 L1 / L2 执行合并：
      - 保留组内 id 字典序最小的
      - 其余写进 aliases（复用 AdaptiveStore 的 _aliases 机制）
      - 从原文件中删除被合并的行
    """
    backup_files(files)

    alias_map = {}  # drop_id -> keep_id
    for g in result["L1"] + result["L2"]:
        keep = sorted(g)[0]
        for drop in g:
            if drop != keep:
                alias_map[drop] = keep

    # 1. 写回每个文件：删掉被合并的行
    for f in files:
        if not os.path.exists(f):
            continue
        kept_lines = []
        with open(f, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    kept_lines.append(line)
                    continue
                if rec.get("id") in alias_map:
                    continue
                kept_lines.append(line)
        with open(f, "w", encoding="utf-8") as fh:
            fh.write("\n".join(kept_lines) + "\n")

    # 2. 记录 aliases 到 theorem_weights.json 的 aliases 字段（复用既有机制）
    weights_path = "theorem_weights.json"
    if os.path.exists(weights_path):
        with open(weights_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    else:
        data = {"weights": {}, "stats": {}, "cooccur_edges": {}, "edge_depth": {}, "aliases": {}}
    data.setdefault("aliases", {})
    data["aliases"].update(alias_map)
    with open(weights_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)

    # 3. 输出合并日志
    log_path = f".bak/dedup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_path, "w", encoding="utf-8") as fh:
        json.dump({
            "L1": result["L1"],
            "L2": result["L2"],
            "aliases": alias_map,
        }, fh, ensure_ascii=False, indent=2)

    print(f"合并完成：删除 {len(alias_map)} 条，aliases 写入 theorem_weights.json")
    print(f"合并日志 → {log_path}")
    print("提示：下次启动 AdaptiveStore 时 load_weights() 会自动应用 aliases。")


# ---------- 6. CLI ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="+", default=["theorems"])
    ap.add_argument("--scan", action="store_true", help="只扫描")
    ap.add_argument("--apply", action="store_true", help="执行合并")
    ap.add_argument("--json", type=str, default=None, help="报告输出到 JSON")
    args = ap.parse_args()

    from dedup_rules import SEMANTIC_EQUIV

    store, files = load_all(args.dirs)
    result = scan(store, SEMANTIC_EQUIV)

    print_report(result, store)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
        print(f"报告已写出 → {args.json}")

    if args.apply:
        apply_merge(result, store, files)


if __name__ == "__main__":
    main()