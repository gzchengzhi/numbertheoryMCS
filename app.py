"""
数论定理证明器 · Web 界面

功能：
  - 自然语言输入（规则 + 本地 LLM）
  - 形式化输入（直接写谓词）
  - 支持带前提的证明
  - 加载全部 424 条定理

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

app = Flask(__name__)


# ============================================================
# 加载所有定理
# ============================================================

def load_all_theorems():
    """加载 theorems.jsonl + theorems/*.jsonl"""
    clauses = []
    paths = ['theorems.jsonl'] + sorted(glob.glob('theorems/*.jsonl'))
    seen_ids = set()

    for path in paths:
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    cid = obj.get('id')
                    if not cid or cid in seen_ids:
                        continue
                    try:
                        head = parse_goal(obj['head'])
                        if head is None:
                            continue
                        body = []
                        for b_str in obj.get('body', []):
                            b = parse_goal(b_str)
                            if b is not None:
                                body.append(b)
                        clauses.append(HornClause(
                            id=cid,
                            name=obj.get('name', cid),
                            head=head,
                            body=body,
                            category=obj.get('category', ''),
                        ))
                        seen_ids.add(cid)
                    except Exception as e:
                        print(f"  [警告] 解析 {cid} 失败: {e}")
                        continue
        except FileNotFoundError:
            continue
    return clauses


print("=" * 60)
print("数论定理证明器 · Web 界面")
print("=" * 60)
print("[1] 加载定理...")
THEOREM_DB = load_all_theorems()
print(f"  加载 {len(THEOREM_DB)} 条定理")
print("=" * 60)


# ============================================================
# 路由
# ============================================================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/theorems')
def api_theorems():
    """返回所有定理"""
    result = []
    for c in THEOREM_DB:
        result.append({
            "id": c.id,
            "name": c.name,
            "category": c.category,
            "head": str(c.head),
            "body": [str(b) for b in c.body],
        })
    return jsonify(result)


def proof_to_dict(proof):
    """ProofStep 列表 → JSON"""
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
            "strategy": step.strategy,
        })
    return result


def try_prove(goal_obj, strategy, var, premises=None):
    """统一证明接口：带前提 + fallback"""
    prover = Prover(THEOREM_DB, max_depth=12)

    if premises:
        # 带前提
        proof = prover.prove_with_premises(
            goal_obj, premises, strategy=strategy, var=var, verbose=False
        )
        # fallback
        if proof is None and strategy != 'direct':
            proof = prover.prove_with_premises(
                goal_obj, premises, strategy='direct', verbose=False
            )
        if proof is None:
            for alt in ['auto', 'contradiction', 'direct']:
                if alt == strategy:
                    continue
                proof = prover.prove_with_premises(
                    goal_obj, premises, strategy=alt, var=var, verbose=False
                )
                if proof:
                    break
    else:
        # 无前提
        proof = prover.prove(goal_obj, strategy=strategy, var=var, verbose=False)
        if proof is None and strategy != 'direct':
            proof = prover.prove(goal_obj, strategy='direct', verbose=False)
        if proof is None:
            for alt in ['auto', 'contradiction', 'direct']:
                if alt == strategy:
                    continue
                proof = prover.prove(goal_obj, strategy=alt, var=var, verbose=False)
                if proof:
                    break

    return proof


@app.route('/api/prove', methods=['POST'])
def api_prove():
    """形式化接口"""
    data = request.get_json()
    goal_str = data.get('goal', '').strip()
    strategy = data.get('strategy', 'auto')
    var_name = data.get('var', '').strip()

    if not goal_str:
        return jsonify({"success": False, "error": "请输入证明目标"})

    goal = parse_goal(goal_str)
    if goal is None:
        return jsonify({
            "success": False,
            "error": f"无法解析: {goal_str}"
        })

    var = Var(var_name) if var_name else None

    try:
        proof = try_prove(goal, strategy, var)
    except Exception as e:
        return jsonify({"success": False, "error": f"证明出错: {str(e)}"})

    if proof is None:
        return jsonify({
            "success": False,
            "error": "未能证明该目标",
            "goal": str(goal),
        })

    return jsonify({
        "success": True,
        "goal": str(goal),
        "proof": proof_to_dict(proof),
        "strategy": strategy,
    })


@app.route('/api/nl_prove', methods=['POST'])
def api_nl_prove():
    """自然语言接口"""
    data = request.get_json()
    query = data.get('query', '').strip()
    use_llm = data.get('use_llm', True)

    if not query:
        return jsonify({"success": False, "error": "请输入问题"})

    # 1. 解析
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
    strategy = parsed.get('strategy', 'auto')
    var_name = parsed.get('var')
    explanation = parsed.get('explanation', '')
    premises_strs = parsed.get('premises', [])

    if not goal_str:
        return jsonify({"success": False, "error": "解析结果缺少 goal"})

    # 2. 解析 goal 和 premises
    goal_obj = parse_goal(goal_str)
    if goal_obj is None:
        return jsonify({"success": False, "error": f"无法解析目标: {goal_str}"})

    premise_objs = []
    for p_str in premises_strs:
        p = parse_goal(p_str)
        if p is not None:
            premise_objs.append(p)

    var = Var(var_name) if var_name else None

    # 3. 证明
    try:
        proof = try_prove(goal_obj, strategy, var, premise_objs if premise_objs else None)
    except Exception as e:
        return jsonify({"success": False, "error": f"证明出错: {str(e)}"})

    if proof is None:
        return jsonify({
            "success": False,
            "error": "未能证明该目标",
            "query": query,
            "parsed": parsed,
        })

    return jsonify({
        "success": True,
        "query": query,
        "parsed": parsed,
        "goal": str(goal_obj),
        "strategy": strategy,
        "proof": proof_to_dict(proof),
    })


# ============================================================
# 启动
# ============================================================

if __name__ == '__main__':
    print("启动后浏览器打开: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host='127.0.0.1', port=5000, debug=False)