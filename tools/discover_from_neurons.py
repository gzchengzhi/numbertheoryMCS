# tools/discover_from_neurons.py
"""15.0.3 神经元 + 神经元 → 新神经元（N≥2）。

输入：theorems/15_0_verified.jsonl（61 条 verified，含 N）
输出：theorems/15_0_new_neurons.jsonl（N≥2 新定理）

组合规则（Cheng 2019 §8.2.4 上层概念逐层形成）：
  A: p(...) :- ... q(...) ...     B: q(...) :- r(...), s(...)
  → C: p(...) :- ... r(...), s(...) ...   （q 被 B.body 替换）
  C.N = max(A.N, B.N) + 1
  C.weight = 0.5^(C.N-1)          （指数衰减）

上限（按计算复杂度动态）：
  max_new = min(500, len(verified) * 8)
  候选组合数 C(61,2)=1830，单次组合代价 O(|A.body| * |B.body|) ≈ 4，
  总代价 ~7320，500 是安全上界。

纪律：
  - 不碰 13.x 定理库
  - 只写 15_0_new_neurons.jsonl
  - 新定理必须过 verify_by_structure
"""
import json
import os
from typing import Dict, List, Optional

from numtheory_prover import HornClause, Pred, Var, Const, unify, substitute
from tools.verify_neuron import verify_by_structure


# ============================================================
# 加载
# ============================================================
def load_verified(path: str = "theorems/15_0_verified.jsonl"
                  ) -> List[Dict]:
    """读 15_0_verified.jsonl，返回原始 dict 列表（含 N）。"""
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def dict_to_clause(rec: Dict) -> Optional[HornClause]:
    """dict → HornClause。"""
    from numtheory_prover import parse_goal
    head = parse_goal(rec["head"])
    body = [parse_goal(b) for b in rec["body"]]
    body = [b for b in body if b is not None]
    if head is None:
        return None
    return HornClause(
        id=rec["id"], name=rec.get("name", rec["id"]),
        head=head, body=body, category=rec.get("category", "自动发现"))


# ============================================================
# 组合
# ============================================================
class NeuronComposer:
    def __init__(self, verified: List[Dict], max_new: int = 500,
                 verbose: bool = False):
        self.verified = verified
        self.max_new = max_new
        self.verbose = verbose
        self.clauses = []
        self.n_map = {}
        for rec in verified:
            c = dict_to_clause(rec)
            if c is not None:
                self.clauses.append(c)
                self.n_map[c.id] = rec.get("N", 1)
        self._seen_sigs = set()

    def compose(self) -> List[Dict]:
        """两两组合，返回新神经元 dict 列表。"""
        new_items: List[Dict] = []
        n_clauses = len(self.clauses)
        if self.verbose:
            print(f"[compose] {n_clauses} 条 verified，"
                  f"候选 C({n_clauses},2)={n_clauses*(n_clauses-1)//2}")

        for i in range(n_clauses):
            if len(new_items) >= self.max_new:
                break
            for j in range(n_clauses):
                if i == j:
                    continue
                if len(new_items) >= self.max_new:
                    break
                a = self.clauses[i]
                b = self.clauses[j]
                new = self._try_compose(a, b)
                if new is None:
                    continue
                # 去重
                sig = (new.head.name,
                       tuple(str(x) for x in new.head.args),
                       tuple(sorted(str(x) for x in new.body)))
                if sig in self._seen_sigs:
                    continue
                self._seen_sigs.add(sig)
                # structure 验证
                if verify_by_structure(new) is not True:
                    continue
                n_new = max(self.n_map.get(a.id, 1),
                            self.n_map.get(b.id, 1)) + 1
                rec = {
                    "id": f"NEURON_NEW::{len(new_items):04d}",
                    "name": f"组合 {a.id} + {b.id}",
                    "head": str(new.head),
                    "body": [str(x) for x in new.body],
                    "N": n_new,
                    "weight": round(0.5 ** (n_new - 1), 4),
                    "composed_from": [a.id, b.id],
                }
                new_items.append(rec)
        if self.verbose:
            print(f"[compose] 生成 {len(new_items)} 条新神经元")
        return new_items

    def _try_compose(self, a: HornClause, b: HornClause
                     ) -> Optional[HornClause]:
        """A.body 某条与 B.head unify → 用 B.body 替换。
    
        15.0.3 补丁：不再跳过 a.head.name == b.head.name，
        因为同 head 但 body 不同的组合能产生新定理（如两个不同的传递链）。
        只跳过「组合后 body 与父完全相同」的情况（由 _seen_sigs 去重）。
        """
        # 删掉：if a.head.name == b.head.name: return None
    
        for idx, body_pred in enumerate(a.body):
            if body_pred.name != b.head.name:
                continue
            if len(body_pred.args) != len(b.head.args):
                continue
            subst = unify(body_pred, b.head, {})
            if subst is None:
                continue
            # 替换
            new_body = []
            ok = True
            for k, bp in enumerate(a.body):
                if k == idx:
                    for bb in b.body:
                        bb_sub = substitute(bb, subst)
                        if type(bb_sub).__name__ != "Pred":
                            ok = False
                            break
                        new_body.append(bb_sub)
                    if not ok:
                        break
                else:
                    new_body.append(bp)
            if not ok:
                continue
            if len(new_body) < 2:
                continue
            # 跳过「组合后 body 与 A.body 完全相同」（自替换）
            if [str(x) for x in new_body] == [str(x) for x in a.body]:
                continue
            return HornClause(
                id="TEMP", name="temp",
                head=a.head, body=new_body, category="自动发现")
        return None


def _collect_vars(clause: HornClause) -> set:
    from numtheory_prover import Var, Const, Pred
    result = set()
    def walk(t):
        if isinstance(t, Var):
            result.add(t.name)
        elif isinstance(t, (Const, Pred)):
            for a in t.args:
                walk(a)
    walk(clause.head)
    for b in clause.body:
        walk(b)
    return result


# ============================================================
# 保存
# ============================================================
def save_new(items: List[Dict],
             path: str = "theorems/15_0_new_neurons.jsonl"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in items:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[save] {len(items)} 条新神经元写入 {path}")


# ============================================================
# 入口
# ============================================================
def discover(verified_path: str = "theorems/15_0_verified.jsonl",
             out_path: str = "theorems/15_0_new_neurons.jsonl",
             max_new: Optional[int] = None,
             verbose: bool = False) -> List[Dict]:
    verified = load_verified(verified_path)
    if not verified:
        if verbose:
            print(f"[discover] {verified_path} 为空")
        return []
    # 上限：min(500, len(verified) * 8)，按计算复杂度
    if max_new is None:
        max_new = min(500, len(verified) * 8)
    composer = NeuronComposer(verified, max_new=max_new, verbose=verbose)
    items = composer.compose()
    save_new(items, out_path)
    return items

def discover_n3(verified_path: str = "theorems/15_0_verified.jsonl",
                n2_path: str = "theorems/15_0_new_neurons.jsonl",
                out_path: str = "theorems/15_0_n3_neurons.jsonl",
                max_new: Optional[int] = None,
                verbose: bool = False) -> List[Dict]:
    """15.0.4：N=1 + N=2 再组合，产出 N=3。

    合并列表：verified（N=1）+ new_neurons（N=2），共 111 条。
    组合后 N = max(A.N, B.N) + 1，所以 N=1 + N=2 → N=3。
    """
    verified = load_verified(verified_path)
    n2 = load_verified(n2_path)  # 同格式
    merged = verified + n2
    if not merged:
        return []
    if max_new is None:
        max_new = min(500, len(merged) * 8)
    composer = NeuronComposer(merged, max_new=max_new, verbose=verbose)
    items = composer.compose()
    # 过滤：只保留 N=3
    items = [it for it in items if it["N"] >= 3]
    save_new(items, out_path)
    return items

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp",
                    default="theorems/15_0_verified.jsonl")
    ap.add_argument("--out", dest="out",
                    default="theorems/15_0_new_neurons.jsonl")
    ap.add_argument("--max-new", type=int, default=None)
    ap.add_argument("-v", "--verbose", action="store_true")
    
    ap.add_argument("--n3", action="store_true",
                    help="N=1 + N=2 再组合，产出 N=3")
    args = ap.parse_args()
    discover(args.inp, args.out, args.max_new, args.verbose) 
    # ...
    if args.n3:
        discover_n3(verbose=args.verbose)
    else:
        discover(args.inp, args.out, args.max_new, args.verbose)    
    
