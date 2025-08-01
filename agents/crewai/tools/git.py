# git.py
from pathlib import Path
import git, os
from langchain.tools import tool


REPO = git.Repo(Path(__file__).resolve().parents[3])

@tool("git_write", return_direct=True)
def git_write(path: str, content: str):
    """Create/overwrite a file and stage it for commit."""
    full = REPO.working_tree_dir + "/" + path
    Path(full).parent.mkdir(parents=True, exist_ok=True)
    Path(full).write_text(content)
    REPO.git.add(path)
    return f"Wrote {path} ({len(content)} bytes)"