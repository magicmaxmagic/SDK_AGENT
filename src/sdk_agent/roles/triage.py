from __future__ import annotations

from sdk_agent.core.base_agent import BaseAgentFactory
from sdk_agent.plugins.base import BaseProjectPlugin


def make_triage_agent(factory: BaseAgentFactory, plugin: BaseProjectPlugin):
    context = plugin.to_context()
    instructions = (
        f"You are the Triage orchestrator for project '{context.project_name}'. "
        "Classify requests as feature, bugfix, plan, validate, or review. "
        "Identify required workflow phases and escalation conditions."
    )
    return factory.create(name="Triage", instructions=instructions)
