from __future__ import annotations

from sdk_agent.core.base_agent import BaseAgentFactory
from sdk_agent.plugins.base import BaseProjectPlugin


def make_release_manager_agent(factory: BaseAgentFactory, plugin: BaseProjectPlugin):
    context = plugin.to_context()
    instructions = (
        f"You are the ReleaseManager for project '{context.project_name}'. "
        "Create release notes, deployment checklist, rollback checklist, and validation summary. "
        "Highlight residual risk and approvals needed before production decisions."
    )
    return factory.create(name="ReleaseManager", instructions=instructions)
