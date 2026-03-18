from __future__ import annotations

from sdk_agent.context import ProjectContext
from sdk_agent.core.base_agent import BaseAgentFactory


def make_developer_agent(
    factory: BaseAgentFactory,
    context: ProjectContext,
    mcp_servers: list | None = None,
):
    instructions = (
        f"You are the Developer for project '{context.project_name}'. "
        f"Repository path: {context.repo_path}. "
        "Use MCP-backed Codex tools to inspect and modify code. "
        "Implement the smallest safe diff, reuse existing patterns, and avoid unrelated changes."
    )
    return factory.create(
        name="Developer",
        instructions=instructions,
        mcp_servers=mcp_servers,
    )
