import subprocess, sys, os
from pathlib import Path

def test_cli_help():
    r = subprocess.run([sys.executable, "-m", "tsscan.cli", "--help"], capture_output=True)
    assert r.returncode == 0
    assert b"scan" in r.stdout

def test_example_scan(tmp_path):
    # copy tiny example
    here = Path(__file__).resolve().parents[1] / "examples" / "tiny_repo"
    dest = tmp_path / "tiny_repo"
    subprocess.check_call(["cp","-r",str(here),str(dest)])
    r = subprocess.run([sys.executable, "-m", "tsscan.cli", "scan", "--repo", str(dest)], capture_output=True)
    assert r.returncode == 0
    assert (dest / "tsscan_out").exists()
