from __future__ import annotations

from dataclasses import dataclass

from sdk_agent.core.artifacts import ArtifactManager
from sdk_agent.core.base_agent import BaseAgentFactory
from sdk_agent.core.workflow_engine import WorkflowEngine
from sdk_agent.plugins.base import BaseProjectPlugin
from sdk_agent.roles import (
    make_deployer_agent,
    make_developer_agent,
    make_planner_agent,
    make_release_manager_agent,
    make_reviewer_agent,
    make_tester_agent,
    make_triage_agent,
)


@dataclass(slots=True)
class AgentTeam:
    planner: object
    developer: object
    tester: object
    reviewer: object
    release_manager: object
    deployer: object
    triage: object
    workflow: WorkflowEngine


def build_team(plugin: BaseProjectPlugin, model: str, max_fix_iterations: int = 2) -> AgentTeam:
    context = plugin.to_context()
    artifact_manager = ArtifactManager(context=context)
    factory = BaseAgentFactory(model=model)

    planner = make_planner_agent(factory=factory, plugin=plugin)
    developer = make_developer_agent(factory=factory, plugin=plugin)
    tester = make_tester_agent(factory=factory, plugin=plugin)
    reviewer = make_reviewer_agent(factory=factory, plugin=plugin)
    release_manager = make_release_manager_agent(factory=factory, plugin=plugin)
    deployer = make_deployer_agent(factory=factory, plugin=plugin)
    triage = make_triage_agent(factory=factory, plugin=plugin)

    workflow = WorkflowEngine(
        context=context,
        plugin=plugin,
        artifact_manager=artifact_manager,
        planner=planner,
        developer=developer,
        tester=tester,
        reviewer=reviewer,
        release_manager=release_manager,
        deployer=deployer,
        triage=triage,
        max_fix_iterations=max_fix_iterations,
    )

    return AgentTeam(
        planner=planner,
        developer=developer,
        tester=tester,
        reviewer=reviewer,
        release_manager=release_manager,
        deployer=deployer,
        triage=triage,
        workflow=workflow,
    )
