from __future__ import annotations

from sdk_agent.core.base_agent import BaseAgentFactory
from sdk_agent.plugins.base import BaseProjectPlugin


def make_architect_agent(factory: BaseAgentFactory, plugin: BaseProjectPlugin):
    context = plugin.to_context()
    instructions = (
        f"You are the Architect for project '{context.project_name}'. "
        "Validate design for scalability, reliability, and security impact. "
        "Provide architecture checks especially for sensitive changes and migrations."
    )
    return factory.create(name="Architect", instructions=instructions)
