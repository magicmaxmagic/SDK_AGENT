import asyncio
from pathlib import Path

from sdk_agent.context import ProjectContext
from sdk_agent.core.artifacts import ArtifactManager
from sdk_agent.core.audit import AuditLogger
from sdk_agent.core.policy_engine import PolicyEngine
from sdk_agent.core.workflow_engine import WorkflowEngine
from sdk_agent.models import AutonomyLevel, EnvironmentType, FlowType, TrustProfile, WorkflowStatus
from sdk_agent.plugins.critical_repo import CriticalRepoPlugin


class DummyAgent:
    def __init__(self, name: str):
        self.name = name
        self.mcp_servers = []


class StubRunner:
    async def run(self, agent, prompt: str) -> str:  # noqa: ARG002
        if agent.name == "reviewer":
            return "No issue | low | none | false | none"
        return "ok"


def _engine(tmp_path: Path) -> WorkflowEngine:
    context = ProjectContext(
        project_name="critical",
        repo_path=tmp_path,
        lint_command="pytest -q",
        test_command="pytest -q",
        autonomy_level=AutonomyLevel.SUGGEST,
        trust_profile=TrustProfile.CRITICAL,
        dry_run=True,
        allowed_commands=["git status", "git diff", "git rev-parse", "pytest"],
    )
    plugin = CriticalRepoPlugin(project_name="critical", repo_path=tmp_path)
    return WorkflowEngine(
        context=context,
        plugin=plugin,
        artifact_manager=ArtifactManager(context=context),
        audit_logger=AuditLogger(run_dir=context.resolved_artifact_root()),
        policy_engine=PolicyEngine(context=context),
        triage=DummyAgent("triage"),
        planner=DummyAgent("planner"),
        architect=DummyAgent("architect"),
        developer=DummyAgent("developer"),
        tester=DummyAgent("tester"),
        reviewer=DummyAgent("reviewer"),
        security_reviewer=DummyAgent("security_reviewer"),
        release_manager=DummyAgent("release_manager"),
        deployer=DummyAgent("deployer"),
        policy_enforcer=DummyAgent("policy_enforcer"),
        runner=StubRunner(),
    )


def test_production_deploy_denied_by_policy(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    state = asyncio.run(engine.run(flow=FlowType.PLAN, request="Plan only"))
    deployed = asyncio.run(engine.deploy_production(run_id=state.run_id))
    assert deployed.final_status in {WorkflowStatus.BLOCKED, WorkflowStatus.FAILED}


def test_production_deploy_requires_explicit_approval(tmp_path: Path) -> None:
    context = ProjectContext(
        project_name="normal",
        repo_path=tmp_path,
        lint_command="pytest -q",
        test_command="pytest -q",
        autonomy_level=AutonomyLevel.PRODUCTION_CANDIDATE,
        trust_profile=TrustProfile.LOW_RISK_SANDBOX,
        environment=EnvironmentType.PRODUCTION,
        allow_production_deploy=True,
        production_approval_validity_minutes=120,
        required_production_approvals=2,
        deploy_production_command="true",
        dry_run=False,
        allowed_commands=["git status", "git diff", "git rev-parse", "pytest", "true"],
    )
    plugin = CriticalRepoPlugin(project_name="normal", repo_path=tmp_path)
    engine = WorkflowEngine(
        context=context,
        plugin=plugin,
        artifact_manager=ArtifactManager(context=context),
        audit_logger=AuditLogger(run_dir=context.resolved_artifact_root()),
        policy_engine=PolicyEngine(context=context),
        triage=DummyAgent("triage"),
        planner=DummyAgent("planner"),
        architect=DummyAgent("architect"),
        developer=DummyAgent("developer"),
        tester=DummyAgent("tester"),
        reviewer=DummyAgent("reviewer"),
        security_reviewer=DummyAgent("security_reviewer"),
        release_manager=DummyAgent("release_manager"),
        deployer=DummyAgent("deployer"),
        policy_enforcer=DummyAgent("policy_enforcer"),
        runner=StubRunner(),
    )
    state = asyncio.run(engine.run(flow=FlowType.PLAN, request="Plan only", allow_production_deploy=True))
    blocked = asyncio.run(engine.deploy_production(run_id=state.run_id))
    assert blocked.final_status == WorkflowStatus.BLOCKED

    approved_one = engine.approve_production(
        run_id=state.run_id,
        approved_by="oncall",
        ticket_id="CHG-1001",
        ticket_source="cab",
        reason="CAB",
    )
    assert approved_one.production_approval is not None

    still_blocked = asyncio.run(engine.deploy_production(run_id=state.run_id))
    assert still_blocked.final_status == WorkflowStatus.BLOCKED

    approved_two = engine.approve_production(
        run_id=state.run_id,
        approved_by="sre",
        ticket_id="CHG-1002",
        ticket_source="jira",
        reason="Second eye",
    )
    assert len(approved_two.production_approvals) == 2

    deployed = asyncio.run(engine.deploy_production(run_id=state.run_id))
    assert deployed.deployment_history
    assert deployed.deployment_history[-1]["target"] == "production"


def test_production_approval_expiry_blocks_deploy(tmp_path: Path) -> None:
    context = ProjectContext(
        project_name="normal",
        repo_path=tmp_path,
        lint_command="pytest -q",
        test_command="pytest -q",
        autonomy_level=AutonomyLevel.PRODUCTION_CANDIDATE,
        trust_profile=TrustProfile.LOW_RISK_SANDBOX,
        environment=EnvironmentType.PRODUCTION,
        allow_production_deploy=True,
        production_approval_validity_minutes=120,
        required_production_approvals=2,
        deploy_production_command="true",
        dry_run=False,
        allowed_commands=["git status", "git diff", "git rev-parse", "pytest", "true"],
    )
    plugin = CriticalRepoPlugin(project_name="normal", repo_path=tmp_path)
    engine = WorkflowEngine(
        context=context,
        plugin=plugin,
        artifact_manager=ArtifactManager(context=context),
        audit_logger=AuditLogger(run_dir=context.resolved_artifact_root()),
        policy_engine=PolicyEngine(context=context),
        triage=DummyAgent("triage"),
        planner=DummyAgent("planner"),
        architect=DummyAgent("architect"),
        developer=DummyAgent("developer"),
        tester=DummyAgent("tester"),
        reviewer=DummyAgent("reviewer"),
        security_reviewer=DummyAgent("security_reviewer"),
        release_manager=DummyAgent("release_manager"),
        deployer=DummyAgent("deployer"),
        policy_enforcer=DummyAgent("policy_enforcer"),
        runner=StubRunner(),
    )
    state = asyncio.run(engine.run(flow=FlowType.PLAN, request="Plan only", allow_production_deploy=True))
    engine.approve_production(
        run_id=state.run_id,
        approved_by="oncall",
        ticket_id="CHG-1001",
        ticket_source="cab",
        reason="CAB",
        expires_in_minutes=-1,
    )
    engine.approve_production(
        run_id=state.run_id,
        approved_by="sre",
        ticket_id="CHG-1002",
        ticket_source="itsm",
        reason="Second eye",
        expires_in_minutes=60,
    )

    blocked = asyncio.run(engine.deploy_production(run_id=state.run_id))
    assert blocked.final_status == WorkflowStatus.BLOCKED


def test_approval_rejects_invalid_ticket_source_and_pattern(tmp_path: Path) -> None:
    context = ProjectContext(
        project_name="normal",
        repo_path=tmp_path,
        lint_command="pytest -q",
        test_command="pytest -q",
        autonomy_level=AutonomyLevel.PRODUCTION_CANDIDATE,
        trust_profile=TrustProfile.LOW_RISK_SANDBOX,
        environment=EnvironmentType.PRODUCTION,
        allow_production_deploy=True,
        production_approval_validity_minutes=120,
        required_production_approvals=3,
        change_ticket_pattern=r"^CHG-[0-9]{4}$",
        allowed_ticket_sources=["cab"],
        deploy_production_command="true",
        dry_run=False,
        allowed_commands=["git status", "git diff", "git rev-parse", "pytest", "true"],
    )
    plugin = CriticalRepoPlugin(project_name="normal", repo_path=tmp_path)
    engine = WorkflowEngine(
        context=context,
        plugin=plugin,
        artifact_manager=ArtifactManager(context=context),
        audit_logger=AuditLogger(run_dir=context.resolved_artifact_root()),
        policy_engine=PolicyEngine(context=context),
        triage=DummyAgent("triage"),
        planner=DummyAgent("planner"),
        architect=DummyAgent("architect"),
        developer=DummyAgent("developer"),
        tester=DummyAgent("tester"),
        reviewer=DummyAgent("reviewer"),
        security_reviewer=DummyAgent("security_reviewer"),
        release_manager=DummyAgent("release_manager"),
        deployer=DummyAgent("deployer"),
        policy_enforcer=DummyAgent("policy_enforcer"),
        runner=StubRunner(),
    )
    state = asyncio.run(engine.run(flow=FlowType.PLAN, request="Plan only", allow_production_deploy=True))
    rejected = engine.approve_production(
        run_id=state.run_id,
        approved_by="oncall",
        ticket_id="BAD-42",
        ticket_source="jira",
        reason="invalid",
    )
    assert rejected.production_approval is None
    assert rejected.errors
    assert "ticket source" in rejected.errors[-1] or "does not match required pattern" in rejected.errors[-1]


def test_staging_quorum_requires_two_approvals(tmp_path: Path) -> None:
    context = ProjectContext(
        project_name="normal",
        repo_path=tmp_path,
        lint_command="pytest -q",
        test_command="pytest -q",
        autonomy_level=AutonomyLevel.STAGING_DEPLOY,
        trust_profile=TrustProfile.LOW_RISK_SANDBOX,
        allow_staging_deploy=True,
        required_staging_approvals=2,
        deploy_staging_command="true",
        dry_run=False,
        allowed_commands=["git status", "git diff", "git rev-parse", "pytest", "true"],
    )
    plugin = CriticalRepoPlugin(project_name="normal", repo_path=tmp_path)
    engine = WorkflowEngine(
        context=context,
        plugin=plugin,
        artifact_manager=ArtifactManager(context=context),
        audit_logger=AuditLogger(run_dir=context.resolved_artifact_root()),
        policy_engine=PolicyEngine(context=context),
        triage=DummyAgent("triage"),
        planner=DummyAgent("planner"),
        architect=DummyAgent("architect"),
        developer=DummyAgent("developer"),
        tester=DummyAgent("tester"),
        reviewer=DummyAgent("reviewer"),
        security_reviewer=DummyAgent("security_reviewer"),
        release_manager=DummyAgent("release_manager"),
        deployer=DummyAgent("deployer"),
        policy_enforcer=DummyAgent("policy_enforcer"),
        runner=StubRunner(),
    )
    state = asyncio.run(engine.run(flow=FlowType.PLAN, request="Plan only", allow_staging_deploy=True))

    blocked = asyncio.run(engine.deploy_staging(run_id=state.run_id))
    assert blocked.final_status == WorkflowStatus.BLOCKED

    engine.approve_staging(
        run_id=state.run_id,
        approved_by="qa",
        ticket_id="INC-9001",
        ticket_source="itsm",
        reason="first",
    )
    still_blocked = asyncio.run(engine.deploy_staging(run_id=state.run_id))
    assert still_blocked.final_status == WorkflowStatus.BLOCKED

    engine.approve_staging(
        run_id=state.run_id,
        approved_by="release",
        ticket_id="INC-9002",
        ticket_source="cab",
        reason="second",
    )
    deployed = asyncio.run(engine.deploy_staging(run_id=state.run_id))
    assert deployed.final_status == WorkflowStatus.COMPLETED


def test_staging_deploy_failure_triggers_automatic_rollback(tmp_path: Path) -> None:
    context = ProjectContext(
        project_name="normal",
        repo_path=tmp_path,
        lint_command="pytest -q",
        test_command="pytest -q",
        autonomy_level=AutonomyLevel.STAGING_DEPLOY,
        trust_profile=TrustProfile.LOW_RISK_SANDBOX,
        allow_staging_deploy=True,
        required_staging_approvals=1,
        deploy_staging_command="false",
        rollback_staging_command="true",
        dry_run=False,
        allowed_commands=["git status", "git diff", "git rev-parse", "pytest", "false", "true"],
    )
    plugin = CriticalRepoPlugin(project_name="normal", repo_path=tmp_path)
    engine = WorkflowEngine(
        context=context,
        plugin=plugin,
        artifact_manager=ArtifactManager(context=context),
        audit_logger=AuditLogger(run_dir=context.resolved_artifact_root()),
        policy_engine=PolicyEngine(context=context),
        triage=DummyAgent("triage"),
        planner=DummyAgent("planner"),
        architect=DummyAgent("architect"),
        developer=DummyAgent("developer"),
        tester=DummyAgent("tester"),
        reviewer=DummyAgent("reviewer"),
        security_reviewer=DummyAgent("security_reviewer"),
        release_manager=DummyAgent("release_manager"),
        deployer=DummyAgent("deployer"),
        policy_enforcer=DummyAgent("policy_enforcer"),
        runner=StubRunner(),
    )
    state = asyncio.run(engine.run(flow=FlowType.PLAN, request="Plan only", allow_staging_deploy=True))
    engine.approve_staging(
        run_id=state.run_id,
        approved_by="qa",
        ticket_id="INC-9001",
        ticket_source="itsm",
        reason="rollback scenario",
    )
    deployed = asyncio.run(engine.deploy_staging(run_id=state.run_id))
    assert deployed.final_status == WorkflowStatus.ROLLBACK_REQUIRED
    assert deployed.rollback_history
    assert deployed.rollback_history[-1]["target"] == "staging"
    assert deployed.rollback_history[-1]["exit_code"] == 0
