from __future__ import annotations

from sdk_agent.core.base_agent import BaseAgentFactory
from sdk_agent.plugins.base import BaseProjectPlugin


def make_policy_enforcer_agent(factory: BaseAgentFactory, plugin: BaseProjectPlugin):
    context = plugin.to_context()
    instructions = (
        f"You are the PolicyEnforcer for project '{context.project_name}'. "
        "Verify every critical action against explicit policy outcomes. "
        "If policy is violated, block progression and require explicit approval."
    )
    return factory.create(name="PolicyEnforcer", instructions=instructions)
