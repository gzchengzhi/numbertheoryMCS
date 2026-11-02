"""12.7 回归测试：120 题基准，99 pass + 21 xfail。"""
import sys, os, json
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from adaptive_store import AdaptiveStore
from recursive_prover import RecursiveProver
from concept_domain import DomainRegistry


# ★ 从 bench_competition 导入 _build_indexes 和 monkey-patch
import tools.bench_competition as bench
_build_indexes = bench._build_indexes

import numtheory_prover
numtheory_prover.ENABLE_SUBST_CONSISTENCY = True
numtheory_prover.ENABLE_EMPTY_LOWER = True   # ★ 13.0.2: C028 的 lower=[] 命中

@pytest.fixture
def rp():
    import glob
    store = AdaptiveStore()
    for f in sorted(glob.glob("theorems/*.jsonl")):
        base = os.path.basename(f)
        if "learn_log" in base or "candidates" in base:
            continue
        store.load_jsonl(f)
    with open(os.path.join(ROOT, "theorems", "concept_neurons.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    store.concept_neurons = data["concept_neurons"]
    store._neurons_built = True
    if hasattr(store, "_head_index"):
        del store._head_index
    if hasattr(store, "_clause_head_index"):
        del store._clause_head_index
    # ★ 13.0.3/13.0.4: 加载 domains/ 的域神经元
    reg = DomainRegistry("domains")
    reg.load_all_into(store)
    return RecursiveProver(store, iso_edges_path=os.path.join(ROOT, "data", "iso_edges.json"))

def load_cases():
    path = os.path.join(ROOT, "tests", "bench", "competition", "cases.jsonl")
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


ALL = load_cases()


def get_case(cid):
    return next(c for c in ALL if c["id"] == cid)


# ============================================================
# 12.7 基线：99 个 pass
# ============================================================
PASS_IDS = [
    # 12.0~12.3 的 49（50 题里除 C028）
    "C001","C002","C003","C004","C005","C006","C007","C008","C009",
    "C010","C011","C012","C013","C014","C015","C016","C017","C018","C019",
    "C020","C021","C022","C023","C024","C025","C026","C027","C028",
    "C029","C030","C031","C032","C033","C034","C035","C036","C037",
    "C038","C039","C040","C041","C042","C043","C044","C045",
    "C046","C047","C048","C049","C050",
    # 12.5 的 30（C051~C080）
    "C051","C052","C053","C054","C055","C056","C057","C058","C059","C060",
    "C061","C062","C063","C064","C065","C066","C067","C068","C069","C070",
    "C071","C072","C073","C074","C075","C076","C077","C078","C079","C080",
    # 12.7 的 20（连分数 4 + p-adic 5 + 二次型 3 + 综合 8）
    "C081","C082","C083","C084","C085","C086",          # 连分数 4
    "C087","C088","C089","C090","C091","C092",   # p-adic 5（C091 也过）
    "C093","C118","C094","C095","C096","C097","C108","C115","C116",                         # 二次型 3
    "C109","C110","C111","C112","C113","C114","C117","C119","C120",   # 综合 6
    # Dirichlet（13.0）
    "C098","C099","C100","C101","C102",
    # 椭圆曲线（13.0）
    "C103","C104","C105","C106","C107",
]

# ============================================================
# 12.7 的 21 个 xfail（12.8 或 13.0 目标）
# ============================================================
XFAIL_IDS = [

    # 嵌套结构（12.8 修 parse_term）
    
    # 假阳性（12.8 修 Prover substitution）
    
    # FALLBACK（12.8 优化）
   
]


@pytest.mark.parametrize("cid", PASS_IDS)
def test_neuron_pass(rp, cid):
    case = get_case(cid)
    proof = rp.prove(case["goal"], premises=case.get("premises", []), verbose=False)
    assert proof is not None, f"{cid} 未证明（基线退化）"
    assert any(s.strategy.startswith("neuron:") for s in proof), \
        f"{cid} 期望 neuron，实际 {[s.strategy for s in proof]}"


# @pytest.mark.parametrize("cid", XFAIL_IDS)
# @pytest.mark.xfail(reason="12.8/13.0 目标", strict=False)
# def test_xfail(rp, cid):
#     case = get_case(cid)
#     proof = rp.prove(case["goal"], premises=case.get("premises", []), verbose=False)
#     if proof is None:
#         pytest.xfail(f"{cid} 未证明")
#     # 检查假阳性
#     from tools.bench_competition import is_suspect
#     if is_suspect(proof):
#         pytest.xfail(f"{cid} 假阳性")
#     # 检查 fallback（非 neuron）
#     strategies = [s.strategy for s in proof]
#     if not any(s.startswith("neuron:") for s in strategies):
#         pytest.xfail(f"{cid} fallback: {strategies}")
#     # 只有 neuron 命中才算 XPASS（说明 12.8 修好了）
#     assert True