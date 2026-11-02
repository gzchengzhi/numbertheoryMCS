# tools/validate_iso_edges.py
import json, re, sys
from pathlib import Path
from jsonschema import validate

# tools/validate_iso_edges.py（路径部分修正）
ROOT = Path(__file__).resolve().parents[1]
SCHEMA  = json.loads((ROOT / "schemas/iso_edge.schema.json").read_text(encoding="utf-8"))
EDGES   = json.loads((ROOT / "data/iso_edges.json").read_text(encoding="utf-8"))
NEURONS = set(json.loads((ROOT / "theorems/concept_neurons.json")
              .read_text(encoding="utf-8"))["concept_neurons"].keys())

NEURON_ID_RE = re.compile(
    r"^NEURON::(S|T|SP)::[A-Za-z0-9_]+(?:<-[A-Za-z0-9_+]+)?(?:::@[0-9]-@[0-9])?::arity=[0-9]+$"
)
ISO_ID_RE = re.compile(
    r"^ISO::(S|T|SP)::[A-Za-z0-9_]+(?:<-[A-Za-z0-9_+]+)?(?:::@[0-9]-@[0-9])?::arity=[0-9]+"
    r"::(S|T|SP)::[A-Za-z0-9_]+(?:<-[A-Za-z0-9_+]+)?(?:::@[0-9]-@[0-9])?::arity=[0-9]+$"
)

def arity_of(nid): return int(re.search(r"arity=(\d+)$", nid).group(1))
def kind_of(nid):  return re.search(r"NEURON::(S|T|SP)::", nid).group(1)

def main():
    errs, warns = [], []
    for e in EDGES["edges"]:
        try: validate(e, SCHEMA)
        except Exception as ex: errs.append(f"[schema] {e.get('id')}: {ex}")
        if not ISO_ID_RE.match(e["id"]):
            errs.append(f"[bad iso id] {e['id']} 不符合 ISO::<kind>::...::<kind>::... 格式")
        for k in ("src", "dst"):
            nid = e[k]
            if not NEURON_ID_RE.match(nid):
                errs.append(f"[bad neuron id] {e['id']}: {k}={nid}")
            if nid not in NEURONS:
                errs.append(f"[missing neuron] {e['id']}: {k}={nid} 不在 concept_neurons.json")
        if NEURON_ID_RE.match(e["src"]) and NEURON_ID_RE.match(e["dst"]):
            if kind_of(e["src"]) != kind_of(e["dst"]) and e["kind"] == "structural":
                warns.append(f"[warn] {e['id']}: structural 同构但类别不同 ({kind_of(e['src'])}↔{kind_of(e['dst'])})")
            a_s, a_d = arity_of(e["src"]), arity_of(e["dst"])
            if a_s != a_d and not any("arity_mismatch" in g for g in e["mapping"].get("domain_guard", [])):
                warns.append(f"[warn] {e['id']}: arity {a_s}↔{a_d} 但 domain_guard 未声明 arity_mismatch")
    for w in warns: print(w)
    if errs:
        print("\n".join(errs)); sys.exit(1)
    print(f"OK: {len(EDGES['edges'])} 条 iso_edge 通过校验；神经元库 {len(NEURONS)} 条")

if __name__ == "__main__":
    main()