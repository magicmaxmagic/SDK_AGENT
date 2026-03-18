from __future__ import annotations

from sdk_agent.context import ProjectContext
from sdk_agent.core.base_agent import BaseAgentFactory


def make_planner_agent(
    factory: BaseAgentFactory,
    context: ProjectContext,
    mcp_servers: list | None = None,
):
    instructions = (
        f"You are the Planner for project '{context.project_name}'. "
        f"Repository path: {context.repo_path}. "
        "Break the request into small, testable tasks with acceptance criteria, risks, and validation steps."
    )
    return factory.create(
        name="Planner",
        instructions=instructions,
        mcp_servers=mcp_servers,
    )
