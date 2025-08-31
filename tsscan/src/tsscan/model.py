from typing import Dict, Optional, List
from pydantic import BaseModel

class Vertex(BaseModel):
    id: str
    kind: str     # service|table|topic|queue|cache|file|lib|cli|config|repo|route|unknown
    role: str     # http_api|kv|sql|events|fs|scheduler|auth|build|test|root|http|runtime|...
    meta: Dict = {}

class Edge(BaseModel):
    src: str
    dst: str
    rel: str      # import|call|read|write|publish|subscribe|spawn|builds|routes|depends|configures|contains|exposes|read_write
    meta: Dict = {}

class Invariants(BaseModel):
    betti: Dict[str,int]     # {"H0":..., "H1":...}
    components: int
    scc_count: int
    cut_vertices: int
    cut_edges: int
    treewidth_est: Optional[int] = None

class Classification(BaseModel):
    type: str
    confidence: float
    rationale: str

class ProjectRecord(BaseModel):
    project_id: str
    repo_path: str
    git_url: Optional[str] = None
    scanned_at: float
    signature: str
    classification: Classification
    invariants: Invariants
    vertex_count: int
    edge_count: int
