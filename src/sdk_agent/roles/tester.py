from __future__ import annotations

from sdk_agent.core.base_agent import BaseAgentFactory
from sdk_agent.plugins.base import BaseProjectPlugin


def make_tester_agent(
    factory: BaseAgentFactory,
    plugin: BaseProjectPlugin,
):
    context = plugin.to_context()
    instructions = (
        f"You are the Tester for project '{context.project_name}'. "
        f"Use test command: {context.test_command}. "
        f"Use lint command: {context.lint_command}.\n"
        "Run deterministic validations, summarize failures with likely root causes, "
        "and recommend minimal code/test updates."
    )
    return factory.create(
        name="Tester",
        instructions=instructions,
    )
