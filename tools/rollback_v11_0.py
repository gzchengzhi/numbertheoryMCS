# tools/rollback_v11_0.py
"""一键回退到 11.0 稳定状态。"""
import shutil, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
BACKUP = ".bak/v11_0_stable_20261101"

FILES = [
    "recursive_prover.py", "adaptive_prover.py", "adaptive_store.py",
    "working_memory.py", "numtheory_prover.py", "concept_triangle.py",
    "sympy_bridge.py", "sympy_decls.py", "theorem_store.py",
    "arithmetic_engine.py", "symbolic.py", "probe.py",
    "theorems/concept_neurons.json",
    "theorems/12_0_competition.jsonl",
    "tests/bench/competition/cases.jsonl",
]

for f in FILES:
    src = os.path.join(BACKUP, os.path.basename(f))
    dst = f
    if os.path.exists(src):
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        shutil.copy2(src, dst)
        print(f"✅ 回退 {f}")
    else:
        print(f"⚠️ 备份不存在: {src}")
print("回退完成，请跑 pytest 确认 99 passed + 21 xfailed")