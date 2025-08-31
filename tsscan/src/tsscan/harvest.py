import os, re, tempfile, shutil
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from .model import Vertex, Edge
from git import Repo as GitRepo

LANG_DETECTORS = {
    ".py": "python", ".js": "javascript", ".ts": "typescript", ".go": "go",
    ".rs": "rust", ".java":"java", ".rb":"ruby", ".php":"php",
}

HTTP_HINTS = [
    r"FastAPI\(", r"Flask\(", r"Django", r"express\(", r"koa\(", r"gin\.",
    r"router\.get\(", r"router\.post\(", r"app\.get\(", r"app\.post\(",
    r"gorilla/mux", r"actix_web", r"springframework\.web"
]
DB_HINTS = [r"psycopg2", r"sqlalchemy", r"pg\.", r"mongoose", r"mysql", r"sqlite3", r"redis", r"dynamodb", r"prisma", r"gorm", r"jdbc"]
QUEUE_HINTS = [r"kafka", r"pulsar", r"rabbitmq", r"sqs", r"pubsub", r"nats"]
AUTH_HINTS = [r"oauth", r"jwt", r"oidc", r"passport", r"auth0", r"firebase auth"]

ROUTE_PATTERNS = [
    r"@app\.get\(['\"](.*?)['\"]", r"@app\.post\(['\"](.*?)['\"]",
    r"app\.get\(['\"](.*?)['\"]", r"app\.post\(['\"](.*?)['\"]",
    r"router\.(?:get|post|put|delete)\(['\"](.*?)['\"]"
]

def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")

def clone_or_use(repo: str) -> Tuple[Path, Optional[str], Optional[Path]]:
    if is_url(repo):
        tmp = Path(tempfile.mkdtemp(prefix="tsscan_"))
        dest = tmp / "repo"
        GitRepo.clone_from(repo, dest, depth=1, no_single_branch=True)
        return dest, repo, tmp
    p = Path(repo).expanduser().resolve()
    if not p.exists():
        raise RuntimeError(f"Path not found: {p}")
    return p, None, None

def walk_files(root: Path) -> List[Path]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        if any(s in dirpath for s in [".git", "node_modules", "venv", ".venv", "dist", "build", "target"]):
            continue
        for f in filenames:
            fp = Path(dirpath) / f
            if fp.suffix.lower() in LANG_DETECTORS or f in ("Dockerfile","docker-compose.yml","package.json","pyproject.toml","requirements.txt","go.mod"):
                files.append(fp)
    return files

def safe_read(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")
    except Exception:
        return ""

def harvest(root: Path) -> Tuple[List[Vertex], List[Edge]]:
    vertices: Dict[str, Vertex] = {}
    edges: List[Edge] = []

    def vkey(kind, role, name): return f"{kind}:{role}:{name}"

    vertices["repo:root"] = Vertex(id="repo:root", kind="repo", role="root", meta={"path": str(root)})

    files = walk_files(root)
    for f in files:
        text = safe_read(f)
        lang = LANG_DETECTORS.get(f.suffix.lower(), "other")
        vid = vkey("file", lang, str(f.relative_to(root)))
        vertices[vid] = Vertex(id=vid, kind="file", role=lang, meta={"path": str(f), "lang": lang})
        edges.append(Edge(src="repo:root", dst=vid, rel="contains", meta={}))

        # crude imports
        if lang == "python":
            for m in re.findall(r"^\s*(?:from|import)\s+([a-zA-Z0-9_\.]+)", text, flags=re.M):
                lid = f"lib:{m}"
                if lid not in vertices: vertices[lid] = Vertex(id=lid, kind="lib", role="runtime", meta={})
                edges.append(Edge(src=vid, dst=lid, rel="import", meta={}))
        if lang in ("javascript","typescript"):
            for m in re.findall(r"(?:import\s+.*?from\s+['\"](.*?)['\"])|(?:require\(['\"](.*?)['\"]\))", text):
                mod = m[0] or m[1]
                if mod:
                    lid = f"lib:{mod}"
                    if lid not in vertices: vertices[lid] = Vertex(id=lid, kind="lib", role="runtime", meta={})
                    edges.append(Edge(src=vid, dst=lid, rel="import", meta={}))

        # HTTP services
        if any(re.search(p, text) for p in HTTP_HINTS):
            api_id = "service:http_api"
            if api_id not in vertices: vertices[api_id] = Vertex(id=api_id, kind="service", role="http_api", meta={})
            edges.append(Edge(src=vid, dst=api_id, rel="routes", meta={}))
            for pat in ROUTE_PATTERNS:
                for m in re.findall(pat, text):
                    path = m if isinstance(m, str) else (m[1] if len(m) > 1 else m[0])
                    rid = f"route:{path}"
                    if rid not in vertices: vertices[rid] = Vertex(id=rid, kind="route", role="http", meta={"path": path})
                    edges.append(Edge(src=api_id, dst=rid, rel="exposes", meta={}))

        # DBs / caches
        if any(re.search(p, text, flags=re.I) for p in DB_HINTS):
            db_id = "table:store"
            if db_id not in vertices: vertices[db_id] = Vertex(id=db_id, kind="table", role="kv_or_sql", meta={})
            edges.append(Edge(src=vid, dst=db_id, rel="read_write", meta={}))

        # queues / topics
        if any(re.search(p, text, flags=re.I) for p in QUEUE_HINTS):
            q_id = "topic:events"
            if q_id not in vertices: vertices[q_id] = Vertex(id=q_id, kind="topic", role="events", meta={})
            edges.append(Edge(src=vid, dst=q_id, rel="publish_or_subscribe", meta={}))

        # auth
        if any(re.search(p, text, flags=re.I) for p in AUTH_HINTS):
            a_id = "service:auth"
            if a_id not in vertices: vertices[a_id] = Vertex(id=a_id, kind="service", role="auth", meta={})
            edges.append(Edge(src=vid, dst=a_id, rel="uses_auth", meta={}))

        # config
        if f.name in ("Dockerfile","docker-compose.yml","package.json","pyproject.toml","requirements.txt","go.mod"):
            cfg_id = f"config:{f.name}"
            vertices[cfg_id] = Vertex(id=cfg_id, kind="config", role=f.name, meta={})
            edges.append(Edge(src=vid, dst=cfg_id, rel="declares", meta={}))

        # CLI candidates
        if re.search(r"argparse|click\.command|typer\.Typer|commander\(", text):
            cli_id = "cli:entry"
            if cli_id not in vertices: vertices[cli_id] = Vertex(id=cli_id, kind="cli", role="entrypoint", meta={})
            edges.append(Edge(src=vid, dst=cli_id, rel="exposes", meta={}))

    # heuristic: connect http_api to store/events if any file references both
    has_api = "service:http_api" in vertices
    if has_api:
        touched_store = any(e.rel == "read_write" and e.dst == "table:store" for e in edges)
        touched_events = any(e.rel == "publish_or_subscribe" and e.dst == "topic:events" for e in edges)
        if touched_store:
            edges.append(Edge(src="service:http_api", dst="table:store", rel="read_write", meta={"heuristic": True}))
        if touched_events:
            edges.append(Edge(src="service:http_api", dst="topic:events", rel="publish", meta={"heuristic": True}))

    return list(vertices.values()), edges
