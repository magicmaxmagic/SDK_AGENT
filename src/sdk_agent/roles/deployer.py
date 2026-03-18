from __future__ import annotations

from sdk_agent.context import ProjectContext
from sdk_agent.core.base_agent import BaseAgentFactory


def make_deployer_agent(
    factory: BaseAgentFactory,
    context: ProjectContext,
    mcp_servers: list | None = None,
):
    staging = context.deploy_staging_command or "No staging deploy command configured."
    production = context.deploy_production_command or "No production command configured."

    instructions = (
        f"You are the Deployer for project '{context.project_name}'. "
        f"Staging command: {staging}. Production command: {production}. "
        "Prepare deploy steps, rollback strategy, and post-deploy verification. "
        "Never execute or recommend automatic production deployment."
    )
    return factory.create(
        name="Deployer",
        instructions=instructions,
        mcp_servers=mcp_servers,
    )
