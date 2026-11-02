# concept_domain.py
"""
13.0 概念域注册机制。

一个 ConceptDomain 是：
- 一组新谓词（dirichlet_character、elliptic_curve 等）
- 一组概念神经元（concept_neurons.json）
- 一组同构边（iso_edges.json，可空）
- 一组测试用例（cases.jsonl）

域独立加载，不污染主库。12.x 的 211 个神经元不动。
"""
import os
import json
import glob
from typing import Optional


class ConceptDomain:
    def __init__(self, name: str, root: str = "domains"):
        self.name = name
        self.root = os.path.join(root, name)
        self.neurons_path = os.path.join(self.root, "concept_neurons.json")
        self.iso_edges_path = os.path.join(self.root, "iso_edges.json")
        self.cases_path = os.path.join(self.root, "cases.jsonl")

    def exists(self) -> bool:
        return os.path.isdir(self.root)

    def load_neurons(self) -> dict:
        """返回域内的神经元字典。"""
        if not os.path.exists(self.neurons_path):
            return {}
        with open(self.neurons_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("concept_neurons", {})

    def load_iso_edges(self) -> dict:
        """返回域内的 iso_edges（原始 JSON）。"""
        if not os.path.exists(self.iso_edges_path):
            return {"edges": []}
        with open(self.iso_edges_path, encoding="utf-8") as f:
            return json.load(f)

    def load_cases(self) -> list:
        """返回域内的测试用例（JSONL）。"""
        if not os.path.exists(self.cases_path):
            return []
        cases = []
        with open(self.cases_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    cases.append(json.loads(line))
        return cases

    def load_into_store(self, store) -> int:
        """
        把域内的神经元合并到 store.concept_neurons。
        不覆盖已有的（主库优先）。
        返回新增的神经元数。
        """
        neurons = self.load_neurons()
        added = 0
        for nid, n in neurons.items():
            if nid not in store.concept_neurons:
                store.concept_neurons[nid] = n
                added += 1
        # 重建 head 索引
        if hasattr(store, "_head_index"):
            del store._head_index
        if hasattr(store, "_clause_head_index"):
            del store._clause_head_index
        return added

    def load_iso_into(self, iso_loader) -> int:
        """
        把域内的 iso_edges 合并到 RecursiveProver 的 iso_index。
        iso_loader 是一个 callable(path) -> dict 的函数（RecursiveProver._load_iso_edges）。
        返回新增的边数。
        """
        if not os.path.exists(self.iso_edges_path):
            return 0
        data = self.load_iso_edges()
        edges = data.get("edges", [])
        return len(edges)


class DomainRegistry:
    """管理所有已注册的域。"""
    def __init__(self, root: str = "domains"):
        self.root = root
        self.domains = {}

    def register(self, name: str) -> ConceptDomain:
        d = ConceptDomain(name, self.root)
        self.domains[name] = d
        return d

    def list_domains(self) -> list:
        if not os.path.isdir(self.root):
            return []
        return sorted([d for d in os.listdir(self.root)
                       if os.path.isdir(os.path.join(self.root, d))])

    def load_all_into(self, store) -> dict:
        """加载所有域到 store，返回 {name: added_count}。"""
        result = {}
        for name in self.list_domains():
            d = self.register(name)
            result[name] = d.load_into_store(store)
        return result