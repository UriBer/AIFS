#!/usr/bin/env python3
"""
CrewAI 0.152 working pipeline.

* Reads crew.yml
* Converts every LangChain StructuredTool -> CrewAI tool via decorator
* No BaseTool objects leak into Agent.tools
"""

import pathlib, yaml, functools
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool as crew_tool

# ---------- repo paths -----------------------------------------------------
ROOT      = pathlib.Path(__file__).resolve().parent
YAML_PATH = ROOT / "crew.yml"

# ---------- your StructuredTool imports -----------------------------------
from tools.git            import git_write
from tools.clippy         import clippy
from tools.pytest_runner  import pytest_runner
from tools.github_pr      import git_push, github_pr

ALL_TOOLS = [git_write, clippy, pytest_runner, git_push, github_pr]

# ---------- helper: StructuredTool → callable ------------------------------
def lift(t):
    @functools.wraps(t.run)
    def _wrapper(*a, **kw):
        return t.run(*a, **kw)
    return _wrapper

# ---------- build agents ---------------------------------------------------
def mk_agents(role_cfgs):
    out = {}
    for rc in role_cfgs:
        want = set(rc.get("tools", []))
        tools = [
            crew_tool(t.name)(lift(t))
            for t in ALL_TOOLS if t.name in want
        ]
        out[rc["name"]] = Agent(
            role      = rc["name"],
            goal      = rc.get("goal", ""),
            backstory = rc.get("backstory", ""),
            tools     = tools,
            verbose   = True,
        )
    return out

# ---------- build tasks ----------------------------------------------------
def mk_tasks(task_cfgs, agents):
    tasks = []
    for tc in task_cfgs:
        if "agent" not in tc:
            continue
        tasks.append(Task(
            description=tc.get("description", tc.get("name", "")),
            expected_output=tc.get("expected_output", "Task completed successfully."),
            agent=agents[tc["agent"]],
            verbose=True
        ))
    return tasks

# ---------- main -----------------------------------------------------------
def main():
    with open(YAML_PATH) as f:
        data = yaml.safe_load(f)
    agents = mk_agents(data["roles"])
    tasks  = mk_tasks(data["tasks"], agents)
    Crew(agents=list(agents.values()),
         tasks=tasks,
         process=Process.sequential,
         verbose=True).kickoff()

if __name__ == "__main__":
    main()