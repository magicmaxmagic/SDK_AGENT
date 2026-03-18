from __future__ import annotations

from sdk_agent.core.base_agent import BaseAgentFactory
from sdk_agent.plugins.base import BaseProjectPlugin


def make_planner_agent(
    factory: BaseAgentFactory,
    plugin: BaseProjectPlugin,
):
    context = plugin.to_context()
    rules = "\n".join(f"- {rule}" for rule in plugin.project_rules())
    instructions = (
        f"You are the Planner for project '{context.project_name}'. "
        f"Repository path: {context.repo_path}.\n"
        "You can inspect repository structure and produce implementation plans only.\n"
        "Do not modify code directly.\n"
        "Always include acceptance criteria, risk matrix, and validation plan.\n"
        f"Project rules:\n{rules}"
    )
    return factory.create(
        name="Planner",
        instructions=instructions,
    )
