"""
10.0 sympy 声明表。
所有声明以"虚拟定理"形式存在于 AdaptiveStore 里，不写入 JSONL。
"""

SYMPY_DECLS = {
    # ========== 基础关系 ==========
    "divides": {
        "predicate": "divides",
        "translate": "lambda a, b: sympy.Eq(sympy.Mod(b, a), 0)",
        "custom_funcs": {},
    },
    "congruent": {
        "predicate": "congruent",
        "translate": "lambda a, b, m: sympy.Eq(sympy.Mod(a - b, m), 0)",
        "custom_funcs": {},
    },
    "Eq": {
        "predicate": "Eq",
        "translate": "lambda lhs, rhs: sympy.Eq(lhs, rhs)",
        "custom_funcs": {},
    },
    
    # ========== 数论性质 ==========
    "prime": {
        "predicate": "prime",
        "translate": "lambda p: sympy.isprime(p)",
        "custom_funcs": {},
    },
    "coprime": {
        "predicate": "coprime",
        "translate": "lambda a, b: sympy.Eq(sympy.gcd(a, b), 1)",
        "custom_funcs": {},
    },
    "irrational": {
        "predicate": "irrational",
        "translate": "lambda x: sympy.simplify(sympy.ask(sympy.Q.irrational(x)))",
        "custom_funcs": {},
    },
    "rational": {
        "predicate": "rational",
        "translate": "lambda x: sympy.simplify(sympy.ask(sympy.Q.rational(x)))",
        "custom_funcs": {},
    },
    "integer": {
        "predicate": "integer",
        "translate": "lambda x: sympy.simplify(sympy.ask(sympy.Q.integer(x)))",
        "custom_funcs": {},
    },
    
    # ========== 函数与运算 ==========
    "sqrt": {
        "predicate": "sqrt",
        "translate": "lambda x: sympy.sqrt(x)",
        "custom_funcs": {},
    },
    "factorial": {
        "predicate": "factorial",
        "translate": "lambda n: sympy.factorial(n)",
        "custom_funcs": {},
    },
    "product_range": {
        "predicate": "product_range",
        "translate": "lambda m, n: sympy.Product(sympy.Symbol('k'), (sympy.Symbol('k'), m, m+n-1))",
        "custom_funcs": {},
    },
    "gcd": {
        "predicate": "gcd",
        "translate": "lambda a, b: sympy.gcd(a, b)",
        "custom_funcs": {},
    },
    "lcm": {
        "predicate": "lcm",
        "translate": "lambda a, b: sympy.lcm(a, b)",
        "custom_funcs": {},
    },
    
    # ========== 比较关系 ==========
    "gt": {
        "predicate": "gt",
        "translate": "lambda a, b: sympy.Gt(a, b)",
        "custom_funcs": {},
    },
    "ge": {
        "predicate": "ge",
        "translate": "lambda a, b: sympy.Ge(a, b)",
        "custom_funcs": {},
    },
    "lt": {
        "predicate": "lt",
        "translate": "lambda a, b: sympy.Lt(a, b)",
        "custom_funcs": {},
    },
    "le": {
        "predicate": "le",
        "translate": "lambda a, b: sympy.Le(a, b)",
        "custom_funcs": {},
    },
}