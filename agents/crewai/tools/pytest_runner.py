# pytest_runner.py
import subprocess, pathlib, textwrap, json
from langchain.tools import tool

REPO_DIR = pathlib.Path(__file__).resolve().parents[3]

@tool("pytest_runner", return_direct=True)
def pytest_runner() -> str:
    """Run pytest and return summary (fail ⇒ raise)."""
    res = subprocess.run(
        ["pytest", "-q"],
        cwd=REPO_DIR,
        text=True,
        capture_output=True
    )
    if res.returncode != 0:
        raise RuntimeError("Tests failed:\n" + res.stdout + res.stderr)
    return res.stdout.strip()