# clippy.py
import subprocess, json, os, pathlib, git
from langchain.tools import tool

REPO_DIR = pathlib.Path(__file__).resolve().parents[3]

@tool("clippy", return_direct=True)
def clippy() -> str:
    """Run cargo clippy and return JSON warnings (truncated)."""
    try:
        out = subprocess.check_output(
            ["cargo", "clippy", "--message-format=json"],
            cwd=REPO_DIR, text=True, stderr=subprocess.STDOUT
        )
        msgs = [json.loads(l) for l in out.splitlines() if '"message"' in l]
        if msgs:
            return "clippy warnings:\n" + json.dumps(msgs[:10], indent=2)  # first 10
        return "clippy clean"
    except subprocess.CalledProcessError as e:
        return f"clippy failed:\n{e.output[:1000]}"