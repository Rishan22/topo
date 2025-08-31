import json, hashlib
from collections import Counter
from typing import List
from .model import Vertex, Edge, Invariants

def canonical_signature(vertices: List[Vertex], edges: List[Edge], inv: Invariants) -> str:
    vc = Counter((v.kind, v.role) for v in vertices)
    ec = Counter(e.rel for e in edges)
    payload = {
        "vc": sorted((f"{k}:{r}", c) for (k,r), c in vc.items()),
        "ec": sorted(ec.items()),
        "inv": dict(inv.betti) | {
            "scc": inv.scc_count, "cutv": inv.cut_vertices, "cute": inv.cut_edges
        }
    }
    j = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(j.encode()).hexdigest()
