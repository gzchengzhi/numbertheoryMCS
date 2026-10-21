"""
数论定理证明器 · Web 界面

功能：
  - 自然语言输入（规则 + 本地 LLM）
  - 形式化输入（直接写谓词）
  - 支持带前提的证明
  - 支持学习新定理（Qwen 返回 new_theorems）
  - 加载全部定理

运行：
  python app.py
然后浏览器打开 http://127.0.0.1:5000
"""

import os
import sys
import json
import glob
import io

# UTF-8 编码（Windows 下必需）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)

from flask import Flask, render_template, request, jsonify

from numtheory_prover import (
    Prover, parse_goal, Var, ProofStep, substitute, HornClause, Pred,
)
from adaptive_store import AdaptiveStore
from adaptive_prover import AdaptiveProver

app = Flask(__name__)


# ============================================================
# 全局 store
# ============================================================
STORE = AdaptiveStore()


def load_all_theorems():
    """加载 build_theorem_db() + theorems.jsonl + theorems/*.jsonl"""
    from numtheory_prover import build_theorem_db

    # 1. 硬编码定理
    for c in build_theorem_db():
        STORE.add(c)

    # 2. JSONL
    paths = ['theorems.jsonl'] + sorted(glob.glob('theorems/*.jsonl'))
    for path in paths:
        if os.path.exists(path):
            try:
                STORE.load_jsonl(path)
            except Exception as e:
                print(f"  [警告] 加载 {path} 失败: {e}")

    # 3. 权重 + 依赖记录
    STORE.load_weights()
    STORE.load_dependency_records()

def save_neurons(self, path: str = "theorems/concept_neurons.json"):
    import json
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        'concept_neurons': dict(self.concept_neurons),
        'neuron_edges': {
            f"{a}|{b}": w for (a, b), w in self.neuron_edges.items()
        },
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_neurons(self, path: str = "theorems/concept_neurons.json"):
    import json
    if not os.path.exists(path):
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return
    self.concept_neurons = data.get('concept_neurons', {})
    self.neuron_edges = {}
    for key, w in data.get('neuron_edges', {}).items():
        parts = key.split("|")
        if len(parts) == 2:
            self.neuron_edges[(parts[0], parts[1])] = w
    self._neurons_built = True

print("=" * 60)
print("数论定理证明器 · Web 界面")
print("=" * 60)
print("[1] 加载定理...")
load_all_theorems()
print(f"  加载 {len(STORE.clauses)} 条定理")

print("[2] 构建概念神经元...")
from concept_triangle import extract_triangles
try:
    STORE.load_neurons()    # 先尝试从文件加载
    if not STORE.concept_neurons:
        STORE.build_neurons_from_theorems(extract_triangles)
        STORE.save_neurons()
    print(f"  {len(STORE.concept_neurons)} 个神经元，{len(STORE.neuron_edges)} 条边")
except Exception as e:
    print(f"  [警告] 构建神经元失败: {e}")
print("=" * 60)


# ============================================================
# 路由
# ============================================================


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/neurons')
def api_neurons():
    """返回所有概念神经元，按实例数降序"""
    result = []
    for nid, n in STORE.concept_neurons.items():
        result.append({
            "neuron_id": nid,
            "type": n["type"],
            "N": n["N"],
            "weight": n["weight"],
            "instance_count": len(n["instances"]),
            "mediator": n.get("mediator"),
            "anchor": n.get("anchor"),
            # 实例样本（前 3 个）
            "samples": [
                {
                    "source_clause": inst.get("source_clause"),
                    "lower": [str(x) for x in inst.get("lower", [])],
                    "mediator": inst.get("mediator"),
                    "anchor": inst.get("anchor"),
                }
                for inst in n["instances"][:3]
            ],
        })
    result.sort(key=lambda x: -x["instance_count"])
    return jsonify(result)


@app.route('/api/neuron_stats')
def api_neuron_stats():
    """神经元统计"""
    from collections import Counter
    types = Counter(n["type"] for n in STORE.concept_neurons.values())
    return jsonify({
        "total": len(STORE.concept_neurons),
        "edges": len(STORE.neuron_edges),
        "by_type": dict(types),
        "total_instances": sum(len(n["instances"]) for n in STORE.concept_neurons.values()),
    })

@app.route('/api/theorems')
def api_theorems():
    result = []
    for c in STORE.clauses:
        result.append({
            "id": c.id,
            "name": c.name,
            "category": c.category,
            "head": str(c.head),
            "body": [str(b) for b in c.body],
        })
    return jsonify(result)


def proof_to_dict(proof):
    if not proof:
        return []
    result = []
    for step in proof:
        body_strs = []
        for b in step.clause.body:
            body_strs.append(str(substitute(b, step.substitution)))
        head_str = str(substitute(step.clause.head, step.substitution))
        result.append({
            "id": step.clause.id,
            "name": step.clause.name,
            "category": step.clause.category,
            "body": body_strs,
            "head": head_str,
            "depth": step.depth,
            "strategy": step.strategy,        # ★ 保证有
        })
    return result


# ============================================================
# 形式化接口
# ============================================================
@app.route('/api/prove', methods=['POST'])
def api_prove():
    data = request.get_json()
    goal_str = data.get('goal', '').strip()
    strategy = data.get('strategy', 'direct')
    var_name = data.get('var', '').strip()
    premises_strs = data.get('premises', [])

    if not goal_str:
        return jsonify({"success": False, "error": "请输入证明目标"})

    goal = parse_goal(goal_str)
    if goal is None:
        return jsonify({"success": False, "error": f"无法解析: {goal_str}"})

    var = Var(var_name) if var_name else None

    try:
        ap = AdaptiveProver(STORE)
        # ★ 先试 direct（最短路径优先）
        proof = ap.prove(goal_str, strategy=strategy, var=var,
                         premises=premises_strs, verbose=False)
        # 失败再试用户指定策略
        if proof is None and strategy != 'direct':
            proof = ap.prove(goal_str, strategy=strategy, var=var,
                             premises=premises_strs, verbose=False)
        # 还失败，试其他策略
        # 还失败，试其他策略
        if proof is None:
            for alt in ['auto', 'contradiction', 'induction']:
                if alt in (strategy, 'direct'):
                    continue
                # ★ 新增：如果没有 var，跳过 induction
                if alt == 'induction' and var is None:
                    continue
                proof = ap.prove(goal_str, strategy=alt, var=var,
                                 premises=premises_strs, verbose=False)
                if proof is not None:
                    break
                
    except Exception as e:
        return jsonify({"success": False, "error": f"证明出错: {str(e)}"})

    if proof is None:
        return jsonify({
            "success": False,
            "error": "未能证明该目标",
            "goal": str(goal),
        })

    STORE.save_weights()
    STORE.save_dependency_records()

    # ★ 识别整体证明路径
    via = 'chain'
    if proof:
        if any(s.strategy.startswith('neuron:') for s in proof):
            via = 'neuron'
        elif any(s.strategy == 'sympy' for s in proof):
            via = 'sympy'

    return jsonify({
        "success": True,
        "goal": str(goal),
        "proof": proof_to_dict(proof),
        "strategy": strategy,
        "via": via,                 # ★ 新增
    })



def _rollback_learned(store, ids):
    """回滚临时吸收的定理（只回滚"本次真新加入的"）"""
    for cid in ids:
        if cid not in store.by_id:
            continue
        c = store.by_id[cid]
        del store.by_id[cid]
        try:
            store.clauses.remove(c)
        except ValueError:
            pass
        if hasattr(store, 'by_predicate'):
            try:
                store.by_predicate[c.head.name].remove(cid)
            except (KeyError, ValueError):
                pass
    # 清空"本次学习标记"
    store._learned_ids = set()
    if ids:
        print(f"[rollback] 回滚 {len(ids)} 条临时定理")


def _persist_learned(new_theorems, proof):
    """
    成功时持久化新定理到 learned.jsonl。
    只持久化"证明链上用到的"定理 —— 避免 Qwen 混入的无用定理污染库。
    """
    # 证明链用到的 id
    used_ids = set(s.clause.id for s in proof)

    # 只保留"用到的"
    to_persist = [t for t in new_theorems if t['id'] in used_ids]
    if not to_persist:
        print(f"[persist] 本次 Qwen 给的新定理都没被用到，跳过")
        return

    learned_file = os.path.join("theorems", "learned.jsonl")
    os.makedirs("theorems", exist_ok=True)

    # 读已有
    existing = set()
    if os.path.exists(learned_file):
        with open(learned_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    existing.add(rec.get("id"))
                except json.JSONDecodeError:
                    pass

    # 写新的
    written = 0
    with open(learned_file, 'a', encoding='utf-8') as f:
        for t in to_persist:
            if t['id'] in existing:
                continue
            rec = {
                "id": t['id'],
                "name": t.get('name', t['id']),
                "category": t.get('category', ''),
                "head": t['head'],
                "body": t.get('body', []),
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            existing.add(t['id'])
            written += 1
    if written:
        print(f"[persist] 写入 {written} 条到 {learned_file}")
        
# ============================================================
# 自然语言接口
# ============================================================
def _try_sympy_shortcut(goal):
    """
    计算层优先：尝试直接通过 sympy 证明目标。
    成功返回 ProofStep 列表，失败返回 None。
    """
    from adaptive_prover import AdaptiveProver
    from numtheory_prover import ProofStep, HornClause
    
    ap = AdaptiveProver(STORE)
    if ap._try_sympy(goal):
        print(f"[sympy] 直接计算成功: {goal} (自然语言接口终极拦截)")
        step = ProofStep(
            clause=HornClause("SYMPY", "sympy 计算", goal, [], category="计算"),
            substitution={},
            subgoal=goal,
            depth=0,
            strategy="sympy",
        )
        return [step]
    return None


@app.route('/api/nl_prove', methods=['POST'])
def api_nl_prove():
    """自然语言接口"""
    data = request.get_json()
    query = data.get('query', '').strip()
    use_llm = data.get('use_llm', True)

    if not query:
        return jsonify({"success": False, "error": "请输入问题"})

    # 1. Qwen 解析
    try:
        from nl_interface import parse_query
        parsed = parse_query(query, use_llm=use_llm, backend='local')
    except Exception as e:
        return jsonify({"success": False, "error": f"解析出错: {str(e)}"})

    if not parsed:
        return jsonify({
            "success": False,
            "error": "无法理解该问题，请换一种表述",
            "query": query,
        })

    goal_str = parsed.get('goal')
    var_name = parsed.get('var')
    premises_strs = parsed.get('premises', [])
    new_theorems = parsed.get('new_theorems', [])
    # 强制放弃 LLM 的 strategy，完全交给系统内部判断
    strategy = 'auto'

    if not goal_str:
        return jsonify({"success": False, "error": "解析结果缺少 goal"})

    goal = parse_goal(goal_str)
    if goal is None:
        return jsonify({"success": False, "error": f"无法解析目标: {goal_str}"})

    # ============================================================
    # ★ 终极拦截：在吸收任何新定理、执行任何复杂逻辑之前，先试 Sympy 计算。
    # 这符合"计算层优先/能量最低消耗"原则。
    # ============================================================
    sympy_proof = _try_sympy_shortcut(goal)
    if sympy_proof is not None:
        return jsonify({
            "success": True,
            "query": query,
            "parsed": parsed,
            "goal": str(goal),
            "strategy": "sympy",
            "learned": [],
            "proof": proof_to_dict(sympy_proof),
            "via": "sympy",
        })

    # ============================================================
    # 下面是原有的逻辑吸收、证明、持久化、回滚流程
    # ============================================================
    
    # 2. 吸收新定理（只记录"真正新加入的"用于回滚）
    marked_ids = []
    newly_added = []

    for t in new_theorems:
        try:
            # 过滤掉 LLM 生成的“定义类”定理，防止污染库
            name = t.get('name', '')
            tid = t.get('id', '')
            if '定义' in name or '_DEF' in tid:
                print(f"[learn] 跳过无用定义: {tid}")
                continue

            head = parse_goal(t['head'])
            if head is None:
                continue
            body = []
            for b_str in t.get('body', []):
                b = parse_goal(b_str)
                if b is not None:
                    body.append(b)
            c = HornClause(
                id=t['id'],
                name=t.get('name', t['id']),
                head=head,
                body=body,
                category=t.get('category', ''),
            )
            if c.id not in STORE.by_id:
                STORE.add(c)
                newly_added.append(c.id)
                print(f"[learn] 临时吸收: {c.id}  {c.name}")
            marked_ids.append(c.id)
        except Exception as e:
            print(f"[learn] 解析 {t.get('id')} 失败: {e}")
            continue

    if marked_ids:
        STORE.mark_learned(marked_ids)
        print(f"[learn] 标记 {len(marked_ids)} 条（其中新增 {len(newly_added)} 条）")

    # 3. 证明
    var = Var(var_name) if var_name else None

    try:
        ap = AdaptiveProver(STORE)
        # 先试 direct（最短路径优先）
        proof = ap.prove(goal_str, strategy='direct', var=var,
                         premises=premises_strs, verbose=False)
        # 失败再试用户指定策略（如果有）
        if proof is None and strategy != 'direct':
            proof = ap.prove(goal_str, strategy=strategy, var=var,
                             premises=premises_strs, verbose=False)
        # 还失败，试其他策略
        if proof is None:
            for alt in ['auto', 'contradiction', 'induction']:
                if alt in (strategy, 'direct'):
                    continue
                # 如果没有 var，跳过 induction
                if alt == 'induction' and var is None:
                    continue
                proof = ap.prove(goal_str, strategy=alt, var=var,
                                 premises=premises_strs, verbose=False)
                if proof is not None:
                    break
    except Exception as e:
        _rollback_learned(STORE, newly_added)
        return jsonify({"success": False, "error": f"证明出错: {str(e)}"})

    # 4. 失败 —— 只回滚"本次真新加入的"
    if proof is None:
        _rollback_learned(STORE, newly_added)
        return jsonify({
            "success": False,
            "error": "未能证明该目标",
            "query": query,
            "parsed": parsed,
        })

    # 5. 成功 —— 持久化"被证明链用到的"新定理
    if new_theorems:
        _persist_learned(new_theorems, proof)

    STORE.save_weights()
    STORE.save_dependency_records()

    # 识别整体证明路径
    via = 'chain'
    if proof:
        if any(s.strategy.startswith('neuron:') for s in proof):
            via = 'neuron'
        elif any(s.strategy == 'sympy' for s in proof):
            via = 'sympy'

    return jsonify({
        "success": True,
        "query": query,
        "parsed": parsed,
        "goal": str(goal),
        "strategy": strategy,
        "learned": newly_added,
        "proof": proof_to_dict(proof),
        "via": via,
    })

# @app.route('/api/neurons')
# def api_neurons():
#     result = []
#     for nid, n in STORE.concept_neurons.items():
#         result.append({
#             'neuron_id': nid,
#             'type': n['type'],
#             'N': n['N'],
#             'weight': n['weight'],
#             'instance_count': len(n['instances']),
#             'mediator': n.get('mediator'),
#             'anchor': n.get('anchor'),
#         })
#     return jsonify(result)


# ============================================================
# 启动
# ============================================================
if __name__ == '__main__':
    print("启动后浏览器打开: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host='127.0.0.1', port=5000, debug=False)