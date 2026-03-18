from sdk_agent.core.base_agent import BaseAgentFactory
from sdk_agent.context import ProjectContext


def make_developer_agent(
    factory: BaseAgentFactory,
    context: ProjectContext,
    tools: list | None = None,
    instructions_override: str | None = None,
    instructions_suffix: str | None = None,
):
    instructions = instructions_override or (
        f"You are a senior software engineer working on the project '{context.project_name}'. "
        f"The repository path is: {context.repo_path}. "
        "Implement the smallest safe change possible. "
        "Reuse existing patterns. Keep diffs small. "
        "Do not introduce unnecessary abstractions."
    )

    if instructions_suffix:
        instructions = f"{instructions}\n\nAdditional project constraints:\n{instructions_suffix}"

    return factory.create(
        name="Developer",
        instructions=instructions,
        tools=tools or [],
    )
