from __future__ import annotations

from sdk_agent.core.base_agent import BaseAgentFactory
from sdk_agent.plugins.base import BaseProjectPlugin


def make_security_reviewer_agent(factory: BaseAgentFactory, plugin: BaseProjectPlugin):
    context = plugin.to_context()
    instructions = (
        f"You are the SecurityReviewer for project '{context.project_name}'. "
        "Review auth, access control, secrets handling, infra, and CI/CD impacts. "
        "Output structured risk findings and mitigation actions."
    )
    return factory.create(name="SecurityReviewer", instructions=instructions)
