import sqlite3, json
from pathlib import Path
from typing import List, Tuple
from .model import ProjectRecord, Vertex, Edge

DB_PATH = Path.home() / ".tsscan" / "tss.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def init():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS projects(
        project_id TEXT PRIMARY KEY,
        repo_path TEXT,
        git_url TEXT,
        scanned_at REAL,
        signature TEXT,
        class_type TEXT,
        class_conf REAL,
        class_rat TEXT,
        inv_betti TEXT,
        inv_components INT,
        inv_scc INT,
        inv_cutv INT,
        inv_cute INT,
        inv_treewidth INT,
        vcount INT,
        ecount INT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS vertices(
        project_id TEXT,
        vid TEXT,
        kind TEXT,
        role TEXT,
        meta TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS edges(
        project_id TEXT,
        src TEXT,
        dst TEXT,
        rel TEXT,
        meta TEXT
    )""")
    con.commit(); con.close()

def save(pr: ProjectRecord, vertices: List[Vertex], edges: List[Edge]):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM projects WHERE project_id=?", (pr.project_id,))
    cur.execute("DELETE FROM vertices WHERE project_id=?", (pr.project_id,))
    cur.execute("DELETE FROM edges WHERE project_id=?", (pr.project_id,))
    cur.execute("""INSERT INTO projects VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        pr.project_id, pr.repo_path, pr.git_url, pr.scanned_at, pr.signature,
        pr.classification.type, pr.classification.confidence, pr.classification.rationale,
        json.dumps(pr.invariants.betti), pr.invariants.components, pr.invariants.scc_count,
        pr.invariants.cut_vertices, pr.invariants.cut_edges, pr.invariants.treewidth_est or 0,
        pr.vertex_count, pr.edge_count
    ))
    for v in vertices:
        cur.execute("INSERT INTO vertices VALUES(?,?,?,?,?)", (pr.project_id, v.id, v.kind, v.role, json.dumps(v.meta)))
    for e in edges:
        cur.execute("INSERT INTO edges VALUES(?,?,?,?,?)", (pr.project_id, e.src, e.dst, e.rel, json.dumps(e.meta)))
    con.commit(); con.close()

def load_all_signatures() -> List[Tuple[str,str,str,float]]:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT project_id, signature, class_type, scanned_at FROM projects")
    rows = cur.fetchall()
    con.close()
    return rows
