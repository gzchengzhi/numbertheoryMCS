# tools/dump_prover.py
import sys, os, inspect
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from numtheory_prover import Prover

methods = ["_prove_recursive", "prove_direct", "prove_by_contradiction", "_try_clause", "_prove_inner"]
for m in methods:
    if hasattr(Prover, m):
        print("=" * 60)
        print(f"Prover.{m}")
        print("=" * 60)
        print(inspect.getsource(getattr(Prover, m)))
    else:
        print(f"[MISSING] Prover.{m} 不存在")