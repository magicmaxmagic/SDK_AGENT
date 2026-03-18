from sdk_agent.core.base_agent import BaseAgentFactory
from sdk_agent.context import ProjectContext


def make_tester_agent(
    factory: BaseAgentFactory,
    context: ProjectContext,
    tools: list | None = None,
    instructions_override: str | None = None,
    instructions_suffix: str | None = None,
):
    instructions = instructions_override or (
        f"You are a QA engineer working on the project '{context.project_name}'. "
        f"The main test command is: {context.test_command}. "
        f"The lint command is: {context.lint_command}. "
        "Validate the changes carefully, identify missing tests, and report issues clearly."
    )

    if instructions_suffix:
        instructions = f"{instructions}\n\nAdditional project constraints:\n{instructions_suffix}"

    return factory.create(
        name="Tester",
        instructions=instructions,
        tools=tools or [],
    )
