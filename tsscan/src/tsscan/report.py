import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from typing import List, Tuple
from .model import ProjectRecord

console = Console()

def print_report(project: ProjectRecord, compare_rows: List[Tuple[str,str,str,float]]):
    console.print(Panel.fit(f"[bold]Project ID:[/] {project.project_id}\n[bold]Repo:[/] {project.repo_path}", box=box.ROUNDED))
    t = Table(box=box.SIMPLE_HEAVY)
    t.add_column("Vertices"); t.add_column("Edges"); t.add_column("Betti(H0,H1)"); t.add_column("SCCs"); t.add_column("Cuts(V/E)")
    t.add_row(str(project.vertex_count), str(project.edge_count),
              f"{project.invariants.betti['H0']},{project.invariants.betti['H1']}",
              str(project.invariants.scc_count),
              f"{project.invariants.cut_vertices}/{project.invariants.cut_edges}")
    console.print(t)

    console.print(Panel.fit(f"[bold]Type:[/] {project.classification.type}  "
                            f"[bold]Confidence:[/] {project.classification.confidence:.2f}\n"
                            f"[italic]{project.classification.rationale}[/]",
                            title="Classification", box=box.ROUNDED))

    prev = compare_rows
    if prev:
        simt = Table(title="Similarity vs Previous Scans", box=box.MINIMAL_DOUBLE_HEAD)
        simt.add_column("Prev Project ID", overflow="fold")
        simt.add_column("Prev Type")
        simt.add_column("Same Signature?")
        simt.add_column("When")
        for pid, sig, ptype, when in prev:
            same = "✅" if sig == project.signature else "—"
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(when))
            simt.add_row(pid, ptype or "—", same, ts)
        console.print(simt)
    else:
        console.print("[dim]No previous scans yet.[/dim]")
