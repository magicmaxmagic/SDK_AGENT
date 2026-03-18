from __future__ import annotations

from dataclasses import dataclass

from sdk_agent.core.artifacts import ArtifactManager
from sdk_agent.core.audit import AuditLogger
from sdk_agent.core.base_agent import BaseAgentFactory
from sdk_agent.core.policy_engine import PolicyEngine
from sdk_agent.core.workflow_engine import WorkflowEngine
from sdk_agent.plugins.base import BaseProjectPlugin
from sdk_agent.roles import (
    make_architect_agent,
    make_deployer_agent,
    make_developer_agent,
    make_planner_agent,
    make_policy_enforcer_agent,
    make_release_manager_agent,
    make_reviewer_agent,
    make_security_reviewer_agent,
    make_tester_agent,
    make_triage_agent,
)


ROLE_CAPABILITY_MATRIX: dict[str, dict[str, bool]] = {
    "triage": {"mcp": False, "shell": False, "write": False},
    "planner": {"mcp": False, "shell": False, "write": False},
    "architect": {"mcp": False, "shell": False, "write": False},
    "developer": {"mcp": True, "shell": True, "write": True},
    "tester": {"mcp": False, "shell": True, "write": False},
    "reviewer": {"mcp": False, "shell": False, "write": False},
    "security_reviewer": {"mcp": False, "shell": False, "write": False},
    "release_manager": {"mcp": False, "shell": False, "write": False},
    "deployer": {"mcp": False, "shell": True, "write": False},
    "policy_enforcer": {"mcp": False, "shell": False, "write": False},
}


@dataclass(slots=True)
class AgentTeam:
    triage: object
    planner: object
    architect: object
    developer: object
    tester: object
    reviewer: object
    security_reviewer: object
    release_manager: object
    deployer: object
    policy_enforcer: object
    workflow: WorkflowEngine


def build_team(plugin: BaseProjectPlugin, model: str, max_fix_iterations: int = 2) -> AgentTeam:
    context = plugin.to_context()
    artifact_manager = ArtifactManager(context=context)
    policy_engine = PolicyEngine(context=context)
    factory = BaseAgentFactory(model=model)

    triage = make_triage_agent(factory=factory, plugin=plugin)
    planner = make_planner_agent(factory=factory, plugin=plugin)
    architect = make_architect_agent(factory=factory, plugin=plugin)
    developer = make_developer_agent(factory=factory, plugin=plugin)
    tester = make_tester_agent(factory=factory, plugin=plugin)
    reviewer = make_reviewer_agent(factory=factory, plugin=plugin)
    security_reviewer = make_security_reviewer_agent(factory=factory, plugin=plugin)
    release_manager = make_release_manager_agent(factory=factory, plugin=plugin)
    deployer = make_deployer_agent(factory=factory, plugin=plugin)
    policy_enforcer = make_policy_enforcer_agent(factory=factory, plugin=plugin)

    overrides = context.role_capability_overrides
    for role_name, agent in {
        "triage": triage,
        "planner": planner,
        "architect": architect,
        "developer": developer,
        "tester": tester,
        "reviewer": reviewer,
        "security_reviewer": security_reviewer,
        "release_manager": release_manager,
        "deployer": deployer,
        "policy_enforcer": policy_enforcer,
    }.items():
        capabilities = dict(ROLE_CAPABILITY_MATRIX[role_name])
        capabilities.update(overrides.get(role_name, {}))
        setattr(agent, "capabilities", capabilities)

    workflow = WorkflowEngine(
        context=context,
        plugin=plugin,
        artifact_manager=artifact_manager,
        audit_logger=AuditLogger(run_dir=context.resolved_artifact_root()),
        policy_engine=policy_engine,
        triage=triage,
        planner=planner,
        architect=architect,
        developer=developer,
        tester=tester,
        reviewer=reviewer,
        security_reviewer=security_reviewer,
        release_manager=release_manager,
        deployer=deployer,
        policy_enforcer=policy_enforcer,
        max_fix_iterations=max_fix_iterations,
    )

    return AgentTeam(
        triage=triage,
        planner=planner,
        architect=architect,
        developer=developer,
        tester=tester,
        reviewer=reviewer,
        security_reviewer=security_reviewer,
        release_manager=release_manager,
        deployer=deployer,
        policy_enforcer=policy_enforcer,
        workflow=workflow,
    )
