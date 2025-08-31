import sys, time, shutil
from pathlib import Path
from typing import Optional
import typer
from rich.progress import Progress
import networkx as nx

from .model import ProjectRecord
from .harvest import clone_or_use, harvest
from .classify import classify
from .signature import canonical_signature
from .diagram import write_graph
from .report import print_report
from . import db

app = typer.Typer(add_completion=False)

def compute_invariants(vertices, edges):
    G = nx.MultiDiGraph()
    for v in vertices: G.add_node(v.id, kind=v.kind, role=v.role)
    for e in edges: G.add_edge(e.src, e.dst, rel=e.rel)

    UG = nx.Graph()
    for u, v, data in G.edges(data=True): UG.add_edge(u, v)

    components = nx.number_connected_components(UG)
    V, E = UG.number_of_nodes(), UG.number_of_edges()
    H0 = components
    H1 = max(0, E - V + components)
    scc_count = nx.number_strongly_connected_components(G)
    cut_vertices = len(list(nx.articulation_points(UG))) if V > 0 else 0
    cut_edges = len(list(nx.bridges(UG))) if V > 0 else 0

    from .model import Invariants
    return Invariants(
        betti={"H0": H0, "H1": H1},
        components=components,
        scc_count=scc_count,
        cut_vertices=cut_vertices,
        cut_edges=cut_edges,
        treewidth_est=None
    )

@app.command()
def scan(
    repo: str = typer.Option(..., help="GitHub URL or local path"),
    project_id: Optional[str] = typer.Option(None, help="Override project id"),
    open_diagram: bool = typer.Option(False, help="Open generated diagram if possible"),
):
    """
    Scan a repo, build topological skeleton, store to DB,
    generate diagram in <repo>/tsscan_out/, and print a sameness report.
    """
    db.init()
    local_path, git_url, tmpdir = clone_or_use(repo)
    try:
        with Progress() as progress:
            progress.add_task("[cyan]Harvesting…", total=None)
            vertices, edges = harvest(local_path)

            progress.add_task("[cyan]Computing invariants…", total=None)
            inv = compute_invariants(vertices, edges)

            progress.add_task("[cyan]Classifying…", total=None)
            cls = classify(vertices, edges, inv)

            progress.add_task("[cyan]Diagramming…", total=None)
            diagram_path = write_graph(local_path, vertices, edges)

        sig = canonical_signature(vertices, edges, inv)
        pid = project_id or (git_url or str(local_path))
        rec = ProjectRecord(
            project_id=pid,
            repo_path=str(local_path),
            git_url=git_url,
            scanned_at=time.time(),
            signature=sig,
            classification=cls,
            invariants=inv,
            vertex_count=len(vertices),
            edge_count=len(edges)
        )
        db.save(rec, vertices, edges)

        compare_rows = db.load_all_signatures()
        print_report(rec, compare_rows)

        typer.echo(f"\nDiagram: {diagram_path}")
        if open_diagram and diagram_path.suffix == ".png":
            if sys.platform == "darwin":
                import subprocess; subprocess.run(["open", str(diagram_path)])
            elif sys.platform.startswith("linux"):
                import subprocess; subprocess.run(["xdg-open", str(diagram_path)])
            elif sys.platform.startswith("win"):
                import os; os.startfile(str(diagram_path))  # type: ignore

    finally:
        if tmpdir and tmpdir.exists():
            shutil.rmtree(tmpdir, ignore_errors=True)

@app.command("list-scans")
def list_scans():
    """List all previous scans in the local DB."""
    db.init()
    rows = db.load_all_signatures()
    from rich.table import Table
    from rich.console import Console
    from rich import box
    console = Console()
    if not rows:
        console.print("[dim]No scans found.[/dim]")
        raise typer.Exit()
    t = Table(box=box.SIMPLE_HEAVY)
    t.add_column("Project ID", overflow="fold")
    t.add_column("Type")
    t.add_column("Scanned At")
    for pid, sig, ptype, when in rows:
        import time
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(when))
        t.add_row(pid, ptype or "—", ts)
    console.print(t)
