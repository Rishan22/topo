from typing import List
from .model import Vertex, Edge, Invariants, Classification

def classify(vertices: List[Vertex], edges: List[Edge], inv: Invariants) -> Classification:
    kinds = {(v.kind, v.role) for v in vertices}
    rels = [e.rel for e in edges]

    def has(kind, role): return (kind, role) in kinds

    if has("service","http_api") and has("table","kv_or_sql"):
        if inv.betti.get("H1",0) in (0,1):
            return Classification(type="crud_api", confidence=0.78,
                                  rationale="HTTP API exposing routes with a backing store; simple cycle structure.")
        return Classification(type="http_service_with_store", confidence=0.70,
                              rationale="HTTP API + data store detected.")
    if has("cli","entrypoint") and any(v.kind=="file" for v in vertices):
        return Classification(type="batch_cli_tool", confidence=0.65,
                              rationale="CLI entrypoint and file ops present.")
    if has("topic","events") and not has("service","http_api"):
        return Classification(type="stream_processor", confidence=0.60,
                              rationale="Event topic without HTTP surface.")
    if has("service","auth") and has("service","http_api"):
        return Classification(type="api_with_auth", confidence=0.66,
                              rationale="Auth references in an API project.")

    return Classification(type="mixed_app", confidence=0.40, rationale="Generic structure; no strong motif.")
