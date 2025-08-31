from pathlib import Path
import subprocess
from typing import List
from .model import Vertex, Edge

def _color_for(kind: str) -> str:
    return {
        "service":"lightblue", "route":"lightblue", "table":"lightyellow",
        "topic":"lightpink", "cli":"lavender", "config":"white",
        "file":"gray90", "lib":"gray80", "repo":"white", "unknown":"white"
    }.get(kind, "white")

def write_graph(root: Path, vertices: List[Vertex], edges: List[Edge]) -> Path:
    out_dir = root / "tsscan_out"
    out_dir.mkdir(exist_ok=True)
    dot_path = out_dir / "skeleton.dot"
    png_path = out_dir / "skeleton.png"

    with open(dot_path, "w") as f:
        f.write("digraph G {\n  rankdir=LR;\n  node [shape=box, style=filled];\n")
        for v in vertices:
            label = f"{v.kind}\\n{v.role}"
            f.write(f"  \"{v.id}\" [label=\"{label}\", fillcolor=\"{_color_for(v.kind)}\"];\n")
        for e in edges:
            f.write(f"  \"{e.src}\" -> \"{e.dst}\" [label=\"{e.rel}\"];\n")
        f.write("}\n")

    try:
        subprocess.run(["dot","-Tpng", str(dot_path), "-o", str(png_path)], check=True)
        return png_path
    except Exception:
        return dot_path
