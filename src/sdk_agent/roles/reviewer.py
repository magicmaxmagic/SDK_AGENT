from __future__ import annotations

from sdk_agent.core.base_agent import BaseAgentFactory
from sdk_agent.plugins.base import BaseProjectPlugin


def make_reviewer_agent(
    factory: BaseAgentFactory,
    plugin: BaseProjectPlugin,
):
    context = plugin.to_context()
    instructions = (
        f"You are the Reviewer for project '{context.project_name}'. "
        "Read-only reviewer mindset: do not implement fixes directly.\n"
        "Inspect changed files, diffs, validation results, and risk areas.\n"
        "Report findings with severity (low/medium/high/critical), impact, and action items."
    )
    return factory.create(
        name="Reviewer",
        instructions=instructions,
    )
