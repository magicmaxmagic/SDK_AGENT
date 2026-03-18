from __future__ import annotations

from sdk_agent.context import ProjectContext
from sdk_agent.core.base_agent import BaseAgentFactory
from sdk_agent.core.workflow import SoftwareDeliveryWorkflow
from sdk_agent.roles.deployer import make_deployer_agent
from sdk_agent.roles.developer import make_developer_agent
from sdk_agent.roles.planner import make_planner_agent
from sdk_agent.roles.reviewer import make_reviewer_agent
from sdk_agent.roles.tester import make_tester_agent


def build_software_team(
    context: ProjectContext,
    model: str | None = None,
    mcp_servers: list | None = None,
) -> dict:
    factory = BaseAgentFactory(model=model)

    planner = make_planner_agent(factory=factory, context=context, mcp_servers=mcp_servers)
    developer = make_developer_agent(factory=factory, context=context, mcp_servers=mcp_servers)
    tester = make_tester_agent(factory=factory, context=context, mcp_servers=mcp_servers)
    reviewer = make_reviewer_agent(factory=factory, context=context, mcp_servers=mcp_servers)
    deployer = make_deployer_agent(factory=factory, context=context, mcp_servers=mcp_servers)

    workflow = SoftwareDeliveryWorkflow(
        planner=planner,
        developer=developer,
        tester=tester,
        reviewer=reviewer,
        deployer=deployer,
    )

    return {
        "planner": planner,
        "developer": developer,
        "tester": tester,
        "reviewer": reviewer,
        "deployer": deployer,
        "workflow": workflow,
    }
