from sdk_agent.core.base_agent import BaseAgentFactory
from sdk_agent.context import ProjectContext


def make_planner_agent(
    factory: BaseAgentFactory,
    context: ProjectContext,
    instructions_override: str | None = None,
    instructions_suffix: str | None = None,
):
    instructions = instructions_override or (
        f"You are a senior technical planner working on the project '{context.project_name}'. "
        f"The repository path is: {context.repo_path}. "
        "Break requests into small implementation steps, acceptance criteria, risks, and validation steps. "
        "Be concrete, pragmatic, and structured."
    )

    if instructions_suffix:
        instructions = f"{instructions}\n\nAdditional project constraints:\n{instructions_suffix}"

    return factory.create(
        name="Planner",
        instructions=instructions,
    )
