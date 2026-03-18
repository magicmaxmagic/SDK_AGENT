from __future__ import annotations

from sdk_agent.context import ProjectContext
from sdk_agent.core.base_agent import BaseAgentFactory


def make_reviewer_agent(
    factory: BaseAgentFactory,
    context: ProjectContext,
    mcp_servers: list | None = None,
):
    instructions = (
        f"You are the Reviewer for project '{context.project_name}'. "
        "Review for correctness, regressions, edge cases, maintainability, and missing tests. "
        "Be strict, concrete, and actionable."
    )
    return factory.create(
        name="Reviewer",
        instructions=instructions,
        mcp_servers=mcp_servers,
    )
