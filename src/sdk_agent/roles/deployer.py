from __future__ import annotations

from sdk_agent.core.base_agent import BaseAgentFactory
from sdk_agent.plugins.base import BaseProjectPlugin


def make_deployer_agent(
    factory: BaseAgentFactory,
    plugin: BaseProjectPlugin,
):
    context = plugin.to_context()
    staging = context.deploy_staging_command or "No staging deploy command configured."

    instructions = (
        f"You are the Deployer for project '{context.project_name}'. "
        f"Staging command: {staging}.\n"
        "Prepare deployment instructions for staging only, with rollback and post-deploy checks.\n"
        "Never trigger production deployment, never recommend auto production rollout."
    )
    return factory.create(
        name="Deployer",
        instructions=instructions,
    )
