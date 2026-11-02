import sys, os, inspect
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from recursive_prover import RecursiveProver

print("=" * 70)
print("RecursiveProver.__init__")
print("=" * 70)
print(inspect.getsource(RecursiveProver.__init__))

print("=" * 70)
print("RecursiveProver._try_recursive")
print("=" * 70)
print(inspect.getsource(RecursiveProver._try_recursive))

print("=" * 70)
print("RecursiveProver._match_head_pattern")
print("=" * 70)
print(inspect.getsource(RecursiveProver._match_head_pattern))

print("=" * 70)
print("RecursiveProver._match_lower")
print("=" * 70)
print(inspect.getsource(RecursiveProver._match_lower))

print("=" * 70)
print("RecursiveProver._neuron_head")
print("=" * 70)
print(inspect.getsource(RecursiveProver._neuron_head))

print("=" * 70)
print("RecursiveProver._arg")
print("=" * 70)
print(inspect.getsource(RecursiveProver._arg))

print("=" * 70)
print("RecursiveProver._load_iso_edges")
print("=" * 70)
print(inspect.getsource(RecursiveProver._load_iso_edges))

print("=" * 70)
print("RecursiveProver.__module__ 文件的 mtime")
print("=" * 70)
import recursive_prover
print(f"file: {recursive_prover.__file__}")
print(f"mtime: {os.path.getmtime(recursive_prover.__file__)}")