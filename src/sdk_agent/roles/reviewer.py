from sdk_agent.core.base_agent import BaseAgentFactory
from sdk_agent.context import ProjectContext


def make_reviewer_agent(
    factory: BaseAgentFactory,
    context: ProjectContext,
    tools: list | None = None,
    instructions_override: str | None = None,
    instructions_suffix: str | None = None,
):
    instructions = instructions_override or (
        f"You are a strict code reviewer working on the project '{context.project_name}'. "
        "Look for bugs, regressions, edge cases, maintainability issues, and missing tests. "
        "Be specific and actionable."
    )

    if instructions_suffix:
        instructions = f"{instructions}\n\nAdditional project constraints:\n{instructions_suffix}"

    return factory.create(
        name="Reviewer",
        instructions=instructions,
        tools=tools or [],
    )
