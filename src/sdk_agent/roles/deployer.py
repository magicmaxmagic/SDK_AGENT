from sdk_agent.core.base_agent import BaseAgentFactory
from sdk_agent.context import ProjectContext


def make_deployer_agent(
    factory: BaseAgentFactory,
    context: ProjectContext,
    tools: list | None = None,
    instructions_override: str | None = None,
    instructions_suffix: str | None = None,
):
    deploy_info = context.deploy_staging_command or "No staging deployment command configured."
    instructions = instructions_override or (
        f"You are a DevOps engineer working on the project '{context.project_name}'. "
        f"Staging deployment command: {deploy_info}. "
        "Prepare deployment steps, health checks, rollback instructions, and post-deploy validation."
    )

    if instructions_suffix:
        instructions = f"{instructions}\n\nAdditional project constraints:\n{instructions_suffix}"

    return factory.create(
        name="Deployer",
        instructions=instructions,
        tools=tools or [],
    )
