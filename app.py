"""
数论定理证明器 · Web 界面

运行：
  pip install flask
  python app.py
然后浏览器打开 http://127.0.0.1:5000
"""

from flask import Flask, render_template, request, jsonify
from numtheory_prover import (
    build_theorem_db, Prover, parse_goal, Var,
    ProofStep, substitute,
)

app = Flask(__name__)

# 全局加载定理库（启动时一次）
THEOREM_DB = build_theorem_db()


def proof_to_dict(proof):
    """把 ProofStep 列表转成 JSON 友好的结构"""
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


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/prove', methods=['POST'])
def api_prove():
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
            "error": f"无法解析: {goal_str}。格式如 prime(3)、irrational(sqrt(2))"
        })

    var = Var(var_name) if var_name else None

    try:
        prover = Prover(THEOREM_DB, max_depth=12)
        proof = prover.prove(goal, strategy=strategy, var=var, verbose=False)
    except Exception as e:
        return jsonify({"success": False, "error": f"证明过程出错: {str(e)}"})

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


@app.route('/api/theorems')
def api_theorems():
    """返回所有定理，供前端展示"""
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


if __name__ == '__main__':
    print("=" * 60)
    print("数论定理证明器 · Web 界面")
    print("=" * 60)
    print(f"定理库: {len(THEOREM_DB)} 条")
    print("启动后浏览器打开: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host='127.0.0.1', port=5000, debug=False)