from __future__ import annotations

from sdk_agent.context import ProjectContext
from sdk_agent.core.base_agent import BaseAgentFactory


def make_tester_agent(
    factory: BaseAgentFactory,
    context: ProjectContext,
    mcp_servers: list | None = None,
):
    instructions = (
        f"You are the Tester for project '{context.project_name}'. "
        f"Use test command: {context.test_command}. "
        f"Use lint command: {context.lint_command}. "
        "Validate changes, list failures, and propose minimal fixes."
    )
    return factory.create(
        name="Tester",
        instructions=instructions,
        mcp_servers=mcp_servers,
    )
