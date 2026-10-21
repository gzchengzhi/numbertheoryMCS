"""
10.0 概念三角形提取器。
输入：一个 HornClause（body 非空）
输出：三角形列表 + 隐含神经元列表
"""
import re

NEURON_TYPE_TRANSITIVE   = "transitive"
NEURON_TYPE_SINGLE       = "single"
NEURON_TYPE_SHARED_PARAM = "shared_param"   # 新增
NEURON_TYPE_POLYGON      = "polygon"

def _has_var(pred_tuple):
    """检查 (pred_name, terms) 里是否有单字母变量"""
    return bool(_vars_of(pred_tuple[1]))

def make_shared_param_neuron_id(head_pred, b1_pred, b2_pred, arity):
    """共享参数型神经元 id。两个 body 谓词名排序，保证 (P,Q) 和 (Q,P) 是同一个。"""
    a, b = sorted([b1_pred, b2_pred])
    return f"NEURON::SP::{head_pred}<-{a}+{b}::arity={arity}"

def extract_triangles(clause, to_sympy=None, store=None):
    """
    clause: HornClause 对象（有 .head, .body, .id）
    to_sympy: callable(term, store) -> sympy_expr | None
    store: AdaptiveStore（传给 to_sympy 用）

    返回：
    {
      'triangles': [...],     # 每层一个三角形
      'neurons': [...],       # 涉及的隐含神经元 id
      'final': (pred_name, terms),
      'mediators': [...],     # 中介变量名列表
      'sympy_body': [...],    # 被判定为 sympy 可算的 body（不参与三角形）
      'theorem_type': 'logic' | 'compute' | 'mixed',
    }
    """
    head = _extract_pred(clause.head)
    body = [_extract_pred(b) for b in clause.body]

    # 去重
    body = _dedupe(body)

    # 情况 0：body 为空 → 事实，不生成三角形
    if not body:
        return {
            'triangles': [], 'neurons': [], 'final': head,
            'mediators': [], 'sympy_body': [],
            'theorem_type': 'fact',     # 原来是 'compute'
        }

    # 动态分类：含变量的 body 一律走三角形，只有常量事实才交给 sympy
    sympy_body, logic_body = [], []
    for b in body:
        if _has_var(b):
            logic_body.append(b)
        elif to_sympy and to_sympy(b, store) is not None:
            sympy_body.append(b)
        else:
            logic_body.append(b)

    # 只有 head 是 sympy 谓词时，sympy_body 才算"计算型"
    head_is_sympy = to_sympy and to_sympy(head, store) is not None
    
    head_is_sympy = to_sympy and to_sympy(head, store) is not None

    # body 全是 sympy 常量事实
    if not logic_body:
        if head_is_sympy:
            return {
                'triangles': [], 'neurons': [], 'final': head,
                'mediators': [], 'sympy_body': sympy_body,
                'theorem_type': 'compute',
            }
        # head 不是 sympy → 这是逻辑规则，走变体型
        nid = make_single_neuron_id(head[0], body[0][0], len(head[1]))
        return {
            'triangles': [{
                'type': NEURON_TYPE_SINGLE,
                'neuron': nid,
                'lower': [body[0]],
                'mediator': None,
                'N': 1,
                'weight': 1.0,
            }],
            'neurons': [nid],
            'final': head,
            'mediators': [],
            'sympy_body': sympy_body,
            'theorem_type': 'logic',
        }

    theorem_type = 'mixed' if sympy_body else 'logic'

    # 变体型：只有一个逻辑 body
    if len(logic_body) == 1:
        b = logic_body[0]
        nid = make_single_neuron_id(head[0], b[0], len(head[1]))
        return {
            'triangles': [{
                'type': NEURON_TYPE_SINGLE,
                'neuron': nid,
                'lower': [b],
                'mediator': None,
                'N': 1,
                'weight': 1.0,
            }],
            'neurons': [nid],
            'final': head,
            'mediators': [],
            'sympy_body': sympy_body,
            'theorem_type': theorem_type,
        }

    # 传递型：找中介变量
    # 找中介变量（共享且在 head 外）和共享参数（共享且在 head 内）
    head_vars = _vars_of(head[1])
    body_vars = [_vars_of(b[1]) for b in logic_body]

    mediators = {}
    shared_params = {}
    for i in range(len(logic_body)):
        for j in range(i + 1, len(logic_body)):
            shared = body_vars[i] & body_vars[j]
            for v in shared:
                if v not in head_vars:
                    # 只有谓词相同，才能构成传递型的中介变量
                    if logic_body[i][0] == logic_body[j][0]:
                        mediators.setdefault(v, []).append((i, j))
                    else:
                        # 谓词不同却共享了变量，说明是跨谓词联合，不是传递链
                        shared_params.setdefault(v, []).append((i, j))
                else:
                    shared_params.setdefault(v, []).append((i, j))

    # 情况 A：无中介
    if not mediators:
        # 情况 A1：body=2 且有共享参数 → 共享参数型三角形
        if len(logic_body) == 2 and shared_params:
            b1, b2 = logic_body[0], logic_body[1]
            anchor = sorted(shared_params.keys())[0]
            nid = make_shared_param_neuron_id(
                head[0], b1[0], b2[0], len(head[1]))
            return {
                'triangles': [{
                    'type': NEURON_TYPE_SHARED_PARAM,
                    'neuron': nid,
                    'lower': [b1, b2],
                    'mediator': None,
                    'anchor': anchor,
                    'N': 1,
                    'weight': 1.0,
                }],
                'neurons': [nid],
                'final': head,
                'mediators': [],
                'sympy_body': sympy_body,
                'theorem_type': theorem_type,
            }

        # 情况 A2：body>=3 或 body=2 但无共享参数 → 不是三角形
        return {
            'triangles': [], 'neurons': [], 'final': head,
            'mediators': [], 'sympy_body': sympy_body,
            'theorem_type': theorem_type,
            'note': 'no mediator, no shared param',
            'polygon': True,

        }

    ordered = sorted(mediators.keys(), key=lambda v: min(mediators[v][0]))
    triangles, neurons, prev = [], [], None

    for k, med in enumerate(ordered):
        (i, j) = mediators[med][0]
        b1, b2 = logic_body[i], logic_body[j]
        pos1 = _pos_of(b1[1], med)
        pos2 = _pos_of(b2[1], med)
        nid = make_transitive_neuron_id(head[0], pos1, pos2, len(head[1]))
        lower = [b1, b2] if k == 0 else [prev, b2]
        triangles.append({
            'type': NEURON_TYPE_TRANSITIVE,
            'neuron': nid,
            'lower': lower,
            'mediator': med,
            'N': k + 1,
            'weight': 0.5 ** k,
            'head_pattern': head,  # ← 新增
        })
        prev = nid
        neurons.append(nid)

    return {
        'triangles': triangles,
        'neurons': neurons,
        'final': head,
        'mediators': ordered,
        'sympy_body': sympy_body,
        'theorem_type': theorem_type,
    }


# ========== 辅助函数 ==========

def _extract_pred(pred_obj):
    """HornClause 的 Pred → ('name', ('arg1', 'arg2', ...))"""
    name = pred_obj.name
    terms = tuple(_term_to_str(a) for a in pred_obj.args)
    return (name, terms)


def _term_to_str(t):
    """把 Pred 的参数转成字符串形式，用于变量检测"""
    tn = type(t).__name__
    if tn == 'Var':
        return t.name
    if tn == 'Const':
        if not t.args:
            return t.name
        return f"{t.name}({','.join(_term_to_str(a) for a in t.args)})"
    if tn == 'Pred':
        return f"{t.name}({','.join(_term_to_str(a) for a in t.args)})"
    return str(t)


def _vars_of(terms):
    """从 terms 里提取所有单字母变量（不递归）"""
    return {t for t in terms if _is_var(t)}


def _is_var(s):
    """单字母（a-z）或 字母+数字（x1, n2, d1）"""
    if not isinstance(s, str):
        return False
    return re.match(r'^[a-z]\d*$', s) is not None


def _pos_of(terms, var):
    """var 在 terms 里的位置"""
    try:
        return terms.index(var)
    except ValueError:
        return -1


def _dedupe(body):
    seen, out = set(), []
    for b in body:
        key = (b[0], tuple(b[1]))
        if key not in seen:
            seen.add(key)
            out.append(b)
    return out


def make_transitive_neuron_id(predicate, pos1, pos2, arity):
    a, b = sorted([pos1, pos2])
    return f"NEURON::T::{predicate}::@{a}-@{b}::arity={arity}"


def make_single_neuron_id(head_pred, body_pred, arity):
    return f"NEURON::S::{head_pred}<-{body_pred}::arity={arity}"