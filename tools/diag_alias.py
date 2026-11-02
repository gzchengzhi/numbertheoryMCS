import sys, os, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from adaptive_store import AdaptiveStore

store = AdaptiveStore()
for f in sorted(glob.glob("theorems/*.jsonl")):
    store.load_jsonl(f)
for f in sorted(glob.glob("theorems/12_0_competition/*.jsonl")):
    store.load_jsonl(f)

print("=" * 60)
print("COMP-* 被 alias 的:")
print("=" * 60)
for k, v in sorted(store._aliases.items()):
    if k.startswith("COMP-"):
        print(f"  {k}  →  {v}")

print("\n" + "=" * 60)
print("COMP-076 / COMP-077 是否在 clauses 里:")
print("=" * 60)
ids = {c.id for c in store.clauses}
for cid in ["COMP-076", "COMP-077"]:
    print(f"  {cid}: {'✅ 在' if cid in ids else '❌ 不在'}")

print("\n" + "=" * 60)
print("COMP-* 总数（唯一 id）:")
print("=" * 60)
comp_ids = sorted({c.id for c in store.clauses if c.id.startswith("COMP-")})
print(f"  {len(comp_ids)} 个")
print(f"  列表: {comp_ids}")