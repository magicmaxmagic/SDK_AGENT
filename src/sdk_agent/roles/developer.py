from __future__ import annotations

from sdk_agent.core.base_agent import BaseAgentFactory
from sdk_agent.plugins.base import BaseProjectPlugin


def make_developer_agent(
    factory: BaseAgentFactory,
    plugin: BaseProjectPlugin,
):
    context = plugin.to_context()
    allowed = "\n".join(f"- {cmd}" for cmd in context.allowed_commands)
    instructions = (
        f"You are the Developer for project '{context.project_name}'. "
        f"Repository path: {context.repo_path}.\n"
        "Use Codex MCP tools to implement approved plan with minimal diff.\n"
        "Never deploy to production. Never push directly to main.\n"
        "Keep code style and architecture consistent with the repository.\n"
        "Allowed deterministic commands:\n"
        f"{allowed}"
    )
    return factory.create(
        name="Developer",
        instructions=instructions,
    )
