"""
sympy 桥接：把 (pred_name, terms) 翻译成 sympy 表达式。
独立模块，不依赖 AdaptiveProver。
"""
import sympy
import re


def to_sympy(term, store):
    """
    term: (pred_name, terms_tuple)
    store: AdaptiveStore（用 find_sympy_decls）
    返回 sympy 表达式，或 None（不能翻译）
    """
    pred, args = term

    decls = store.find_sympy_decls(pred)
    if not decls:
        print(f"[DEBUG to_sympy] {pred} 没有声明")
        return None

    # 收集 custom_funcs
    custom = {}
    for d in decls:
        custom.update(d.get('custom_funcs', {}))

    # 构造 env
    env = {'sympy': sympy, **custom}
    for a in args:
        for v in _extract_vars(a):
            env[v] = sympy.Symbol(v)

    # 逐个试 translate
    for d in decls:
        try:
            fn = eval(d['translate'], env)
            sympy_args = [_to_sympy_arg(a, store) for a in args]
            print(f"[DEBUG to_sympy] {pred} 参数翻译结果: {sympy_args}")
            if any(x is None for x in sympy_args):
                print(f"[DEBUG to_sympy] {pred} 有参数是 None，跳过")
                continue
            result = fn(*sympy_args)
            print(f"[DEBUG to_sympy] {pred} 计算结果: {result}")
            return result
        except Exception as e:
            print(f"[DEBUG to_sympy] {pred} 异常: {e}")
            continue

    return None


def _to_sympy_arg(arg, store):
    """递归翻译参数。arg 是字符串。"""
    if not isinstance(arg, str):
        return None

    # 函数调用：name(arg1, arg2, ...)
    m = re.match(r'^(\w+)\((.+)\)$', arg)
    if m:
        fn_name = m.group(1)
        inner_args_str = _split_args(m.group(2))
        
        # 1. 先查声明表
        decls = store.find_sympy_decls(fn_name)
        if decls:
            result = to_sympy((fn_name, tuple(inner_args_str)), store)
            if result is not None:
                return result
                
        # 2. 查 sympy 内置函数（比如 sqrt, plus, times）
        # 注意：这里我们需要处理 plus -> Add, times -> Mul 等
        SYMPY_ALIASES = {
            'plus': 'Add', 'times': 'Mul', 'minus': 'Sub', 'div': 'div',
            'pow': 'Pow', 'power': 'Pow', 'sqrt': 'sqrt', 'factorial': 'factorial'
        }
        if fn_name in SYMPY_ALIASES:
            sympy_name = SYMPY_ALIASES[fn_name]
            fn = getattr(sympy, sympy_name, None)
            if fn is not None:
                inner_args = [_to_sympy_arg(a, store) for a in inner_args_str]
                if all(x is not None for x in inner_args):
                    return fn(*inner_args)
                    
        # 3. 如果都不认识，当作符号处理
        return sympy.Symbol(arg)

    # 数字
    if arg.isdigit():
        return sympy.Integer(int(arg))

    # 单字母或标识符 → 符号
    if re.match(r'^[a-zA-Z_]\w*$', arg):
        return sympy.Symbol(arg)

    # 其他（运算符表达式等）
    try:
        return sympy.sympify(arg)
    except Exception:
        return None


def _extract_vars(arg):
    """从字符串 arg 里提取单字母变量"""
    if not isinstance(arg, str):
        return []
    if re.match(r'^[a-zA-Z]$', arg):
        return [arg]
    m = re.match(r'^(\w+)\((.+)\)$', arg)
    if m:
        out = []
        for a in _split_args(m.group(2)):
            out.extend(_extract_vars(a))
        return out
    return []


def _split_args(s):
    """按逗号分割，忽略括号内的逗号"""
    args, depth, cur = [], 0, ""
    for ch in s:
        if ch == "," and depth == 0:
            args.append(cur.strip())
            cur = ""
        else:
            if ch in "([":
                depth += 1
            elif ch in ")]":
                depth -= 1
            cur += ch
    if cur.strip():
        args.append(cur.strip())
    return args