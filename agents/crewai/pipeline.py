#!/usr/bin/env python3
"""
Pipeline for CrewAI >= 0.150 (tested on 0.152.0).

* Reads roles/tasks from agents/crewai/crew.yml
* Builds Agent and Task objects manually (load_crew_yaml was removed)
* Runs the crew sequentially
"""

import pathlib, yaml
from crewai import Agent, Task, Crew, Process

# ---------- paths ----------------------------------------------------------
ROOT      = pathlib.Path(__file__).resolve().parents[2]
YAML_PATH = ROOT / "agents/crewai" / "crew.yml"
SPEC_PATH = ROOT / "docs/spec/rfc/0001-aifs-architecture.md"

# ---------- import the tool callables --------------------------------------
from tools.git            import git_write
from tools.clippy         import clippy
from tools.pytest_runner  import pytest_runner
from tools.github_pr      import git_push, github_pr

ALL_TOOLS = [git_write, clippy, pytest_runner, git_push, github_pr]

# ---------- helpers --------------------------------------------------------
def build_agents(role_list: list[dict]) -> dict[str, Agent]:
    """Return {role_name: Agent(...)} with tool-spec dicts (not BaseTool)."""
    agents = {}

    for role_cfg in role_list:
        role_name     = role_cfg["name"]
        desired_names = set(role_cfg.get("tools", []))

        crew_tools = []
        for t in ALL_TOOLS:
            if t.name in desired_names:
                crew_tools.append(
                    {
                        "name":        t.name,
                        "description": t.description or (t.__doc__ or t.name),
                        "function":    t.run,   # StructuredTool exposes .run()
                    }
                )

        agents[role_name] = Agent(
            role      = role_name,
            goal      = role_cfg.get("goal", ""),
            backstory = role_cfg.get("backstory", ""),
            tools     = crew_tools,      # <-- list[dict] per spec
            verbose   = True,
        )

    return agents

def build_tasks(task_list: list[dict], agents: dict[str, Agent]) -> list[Task]:
    tasks = []
    for task_cfg in task_list:
        # YAML may contain helper tasks without an agent (e.g., ReadSpec);
        # skip them here—they can be handled in code if ever needed.
        if "agent" not in task_cfg:
            continue
        tasks.append(
            Task(
                description     = task_cfg["description"],
                agent           = agents[task_cfg["agent"]],
                expected_output = task_cfg.get("expected_output", ""),
                output_file     = task_cfg.get("output_file"),
                verbose         = True
            )
        )
    return tasks

# ---------- main entry -----------------------------------------------------
def main() -> None:
    with open(YAML_PATH) as f:
        crew_yaml = yaml.safe_load(f)

    spec_text = SPEC_PATH.read_text()

    agents = build_agents(crew_yaml["roles"])
    tasks  = build_tasks(crew_yaml["tasks"], agents)

    crew = Crew(
        agents  = list(agents.values()),
        tasks   = tasks,
        memory  = {"spec": spec_text},   # shared across all agents
        process = Process.sequential,
        verbose = True
    )
    crew.kickoff()

if __name__ == "__main__":
    main()