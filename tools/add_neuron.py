#!/usr/bin/env python3
"""
安全地向 concept_neurons.json 添加神经元。
- 读原文件
- 合并新神经元（已存在则更新）
- 校验 JSON 合法性（写临时文件再读回）
- 备份原文件
- 原子写回

用法：
    python tools/add_neuron.py
（编辑文件底部的 NEW_NEURONS 字典即可）
"""
import sys, os, json, shutil
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

NEURONS_PATH = os.path.join(ROOT, "theorems", "concept_neurons.json")


# ============================================================
# 在这里定义要添加的神经元
# ============================================================
NEW_NEURONS = {

    "NEURON::S::or::arity=0": {
        "neuron_id": "NEURON::S::or::arity=0",
        "type": "single",
        "lower": [],
        "mediator": None,
        "anchor": None,
        "head_pattern": ["or", ["divides(3,a)", "or(divides(3,b), divides(3,plus(a,b)))"]],
        "N": 1,
        "weight": 1.0,
        "instances": [],
    },
    "NEURON::S::equals<-forall::arity=2": {
        "neuron_id": "NEURON::S::equals<-forall::arity=2",
        "type": "single",
        "lower": [["forall", ["p", "implies(divides(p,n), prime(p))"]]],
        "mediator": None,
        "anchor": None,
        "head_pattern": ["equals", ["phi(n)", "times(n, product(minus(1, div(1,p)))))"]],
        "N": 1,
        "weight": 1.0,
        "instances": [],
    },

}


def main():
    # 1. 读原文件（如果损坏，报错退出，不要覆盖）
    if not os.path.exists(NEURONS_PATH):
        print(f"❌ 文件不存在: {NEURONS_PATH}")
        sys.exit(1)
    try:
        with open(NEURONS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ 原文件已损坏，无法读取: {e}")
        print(f"   位置: line {e.lineno} col {e.colno} (char {e.pos})")
        print(f"   请先修复或从备份恢复，再运行本脚本。")
        sys.exit(1)

    neurons = data.setdefault("concept_neurons", {})
    edges = data.setdefault("neuron_edges", {})
    print(f"[before] neurons: {len(neurons)}, edges: {len(edges)}")

    # 2. 备份
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = os.path.join(ROOT, ".bak", f"concept_neurons_{ts}.json")
    os.makedirs(os.path.dirname(bak), exist_ok=True)
    shutil.copy2(NEURONS_PATH, bak)
    print(f"[backup] → {bak}")

    # 3. 合并
    added, updated, skipped = [], [], []
    for nid, neuron in NEW_NEURONS.items():
        if nid in neurons:
            neurons[nid] = neuron
            updated.append(nid)
        else:
            neurons[nid] = neuron
            added.append(nid)
    print(f"[merge] added: {len(added)}, updated: {len(updated)}")
    for nid in added:
        print(f"  + {nid}")
    for nid in updated:
        print(f"  ~ {nid}")

    # 4. 校验（写临时文件读回）
    tmp = NEURONS_PATH + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        with open(tmp, "r", encoding="utf-8") as f:
            check = json.load(f)
        assert len(check["concept_neurons"]) == len(neurons), "神经元数量不一致"
    except Exception as e:
        print(f"❌ 校验失败，不写回原文件: {e}")
        if os.path.exists(tmp):
            os.remove(tmp)
        sys.exit(1)

    # 5. 原子替换
    os.replace(tmp, NEURONS_PATH)
    print(f"[after] neurons: {len(neurons)}, edges: {len(edges)}")
    print(f"✅ 已写入 {NEURONS_PATH}")


if __name__ == "__main__":
    main()