#!/usr/bin/env python3
"""12.0 学习管线（一键版）：discover → auto-judge → commit。
自动判定规则见 judge()，所有决策写日志 theorems/12_0_learn_log.jsonl。

用法：
    python tools/learn_12_0.py            # 完整跑（discover + judge + commit）
    python tools/learn_12_0.py --dry-run  # 只判定，不写文件
"""
import sys, os, json, glob, shutil, argparse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from adaptive_store import AdaptiveStore
from concept_triangle import extract_triangles
from sympy_bridge import to_sympy

NEURONS = "theorems/concept_neurons.json"
LOG = "logs/12_0_learn_log.jsonl"

# ============================================================
# 自动判定规则
# ============================================================
# 谓词"可用性"分级：lower 里全是这些谓词 → 活图式，可保留
PRED_GOOD = {
    "divides", "congruent", "prime", "coprime", "gt", "ge", "lt", "le",
    "equals", "nonzero", "odd", "even", "not_divides", "not_prime",
    "quadratic_residue", "perfect", "phi", "sigma", "factorial",
    "power", "times", "plus", "minus", "abs", "gcd",
}
# 谓词"高危"分级：lower 里含这些 → 大概率死图式，drop
PRED_BAD = {
    "exists", "forall", "not", "or", "and", "implies",
    "pairwise_coprime", "product", "product_power", "sum",
    "prime_power_in", "legendre", "ord", "in_set", "rational", "irrational",
    "consistent", "quadratic_nonresidue",
}


def _pred_of(low):
    """从 lower 的一项提取谓词名。"""
    if isinstance(low, (list, tuple)) and len(low) >= 1:
        return low[0]
    if isinstance(low, str) and low.startswith("NEURON::"):
        # 子神经元引用：解析 id 里 ::<pred><- 形式
        for seg in low.split("::"):
            if "<-" in seg:
                return seg.split("<-")[0]
        return None
    return None


def judge(rec):
    """返回 (decision, reason)。decision ∈ {keep, drop}。"""
    nid = rec["neuron_id"]
    lower = rec.get("lower") or []
    hp = rec.get("head_pattern")
    already = rec.get("already_exists", False)

    # 规则 1：已存在 → drop（不重复加）
    if already:
        return "drop", "already_exists"

    # 规则 2：lower 为空 → drop（无前置，无法匹配 premises）
    if not lower:
        return "drop", "lower_empty"

    # 规则 3：lower 含高危谓词 → drop
    preds = [_pred_of(l) for l in lower]
    bad = [p for p in preds if p in PRED_BAD]
    if bad:
        return "drop", f"bad_pred:{','.join(str(b) for b in bad)}"

    # 规则 4：lower 里有任何谓词不在 GOOD 也不在 BAD → 保守 drop
    unknown = [p for p in preds if p and p not in PRED_GOOD and p not in PRED_BAD]
    if unknown:
        return "drop", f"unknown_pred:{','.join(str(u) for u in unknown)}"

    # 规则 5：S 型 + hp=None + lower 只有 1 项 → 弱图式，drop
    # （单谓词 S 型只有 source 定理在 clauses 里时才能靠 _try_activate_neurons 命中）
    if rec.get("type") == "single" and hp is None and len(lower) <= 1:
        return "drop", "weak_single_hp_none"

    # 规则 6：T 型（传递）→ keep（传递是核心图式）
    if rec.get("type") == "transitive":
        return "keep", "transitive_core"

    # 规则 7：SP 型，共享参数，lower 全是 good 谓词 → keep
    if rec.get("type") == "shared_param":
        return "keep", "shared_param_good"

    # 规则 8：S 型，hp 非 None，lower 全是 good → keep
    if rec.get("type") == "single" and hp is not None:
        return "keep", "single_with_hp"

    # 规则 9：S 型，hp=None，lower >= 2 且全是 good → 谨慎 keep
    # 这种能走 _try_activate_neurons（前提 source 在 clauses 里）
    if rec.get("type") == "single" and hp is None and len(lower) >= 2:
        return "keep", "single_multi_lower"
    
    

    return "drop", "default_drop"


# ============================================================
# 主流程
# ============================================================
def load_store():
    store = AdaptiveStore()
    for f in sorted(glob.glob("theorems/*.jsonl")):
        store.load_jsonl(f)
    if os.path.exists(NEURONS):
        store.load_neurons(NEURONS)
    return store


def discover(store):
    """为所有 COMP 定理产候选三角形（不写入 store）。"""
    existing = set(store.concept_neurons.keys())
    comp_clauses = [c for c in store.clauses if c.id.startswith("COMP-")]
    print(f"[discover] 已有神经元: {len(existing)}，COMP 定理: {len(comp_clauses)}")

    seen = set()
    candidates = []
    for c in comp_clauses:
        if c.id in store._aliases:
            continue
        try:
            r = extract_triangles(c, to_sympy, store)
        except Exception:
            continue
        for tri in r["triangles"]:
            nid = tri["neuron"]
            if nid in seen:
                continue
            seen.add(nid)
            candidates.append({
                "neuron_id": nid,
                "type": tri.get("type"),
                "lower": tri.get("lower"),
                "mediator": tri.get("mediator"),
                "anchor": tri.get("anchor"),
                "head_pattern": tri.get("head_pattern"),
                "N": tri.get("N", 1),
                "weight": tri.get("weight", 1.0),
                "source_clause": c.id,
                "already_exists": nid in existing,
            })
    print(f"[discover] 候选总数: {len(candidates)}，"
          f"其中新: {sum(1 for x in candidates if not x['already_exists'])}，"
          f"已存在: {sum(1 for x in candidates if x['already_exists'])}")
    return candidates


def commit(store, to_keep):
    """把 to_keep 列表里的候选写入 store.concept_neurons 并保存。"""
    before = len(store.concept_neurons)
    n_added = 0
    for rec in to_keep:
        nid = rec["neuron_id"]
        if nid in store.concept_neurons:
            continue
        tri = {
            "neuron": nid,
            "type": rec["type"],
            "lower": rec["lower"],
            "mediator": rec.get("mediator"),
            "anchor": rec.get("anchor"),
            "head_pattern": rec.get("head_pattern"),
            "N": rec.get("N", 1),
            "weight": rec.get("weight", 1.0),
        }
        store.add_triangle(tri, rec["source_clause"])
        n_added += 1
    after = len(store.concept_neurons)
    print(f"[commit] 新增 {n_added} 个，神经元 {before} → {after}")

    # 备份 + 保存
    os.makedirs(".bak", exist_ok=True)
    bak = f".bak/concept_neurons_before_learn_{after}.json"
    shutil.copy2(NEURONS, bak)
    store.save_neurons(NEURONS)
    print(f"[commit] 备份 → {bak}")
    print(f"[commit] 写入 → {NEURONS}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只判定，不写文件")
    args = ap.parse_args()

    store = load_store()
    candidates = discover(store)

    # 自动判定
    keep, drop = [], []
    for rec in candidates:
        decision, reason = judge(rec)
        rec["decision"] = decision
        rec["reason"] = reason
        if decision == "keep":
            keep.append(rec)
        else:
            drop.append(rec)

    # 写日志
    with open(LOG, "w", encoding="utf-8") as f:
        for rec in candidates:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[judge] keep: {len(keep)}, drop: {len(drop)}")
    print(f"[judge] 决策日志 → {LOG}")

    # 打印 keep 的详细清单
    if keep:
        print("\n[keep] 决定保留的神经元：")
        for rec in keep:
            print(f"  + {rec['neuron_id']}")
            print(f"      type={rec['type']}  source={rec['source_clause']}  reason={rec['reason']}")
            print(f"      lower={rec['lower']}")
            if rec.get("head_pattern"):
                print(f"      hp={rec['head_pattern']}")

    # 打印 drop 的简要清单
    if drop:
        print("\n[drop] 决定丢弃的神经元（按 reason 分组）：")
        from collections import Counter
        by_reason = Counter(r["reason"] for r in drop)
        for reason, n in by_reason.most_common():
            print(f"  ({n:>3}) {reason}")

    if args.dry_run:
        print("\n[dry-run] 不写文件，退出")
        return

    commit(store, keep)
    print(f"\n✅ 完成。审核日志: {LOG}")


if __name__ == "__main__":
    main()