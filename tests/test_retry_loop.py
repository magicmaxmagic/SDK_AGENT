import asyncio
from pathlib import Path

from sdk_agent.context import ProjectContext
from sdk_agent.core.artifacts import ArtifactManager
from sdk_agent.core.audit import AuditLogger
from sdk_agent.core.policy_engine import PolicyEngine
from sdk_agent.core.ticket_connectors import build_ticket_connector
from sdk_agent.core.workflow_engine import WorkflowEngine
from sdk_agent.models import AutonomyLevel, CommandResult, FlowType, TrustProfile
from sdk_agent.plugins.generic import GenericProjectPlugin


class DummyAgent:
    def __init__(self, name: str):
        self.name = name
        self.mcp_servers = []


class StubRunner:
    async def run(self, agent, prompt: str) -> str:  # noqa: ARG002
        if agent.name in {"reviewer", "security_reviewer"}:
            return "No issue | low | none | false | none"
        return "ok"


def _engine(tmp_path: Path) -> WorkflowEngine:
    context = ProjectContext(
        project_name="demo",
        repo_path=tmp_path,
        lint_command="pytest -q",
        test_command="pytest -q",
        autonomy_level=AutonomyLevel.IMPLEMENT,
        trust_profile=TrustProfile.NORMAL_INTERNAL,
        dry_run=True,
        allowed_commands=["git status", "git diff", "git rev-parse", "git checkout -b", "git worktree add", "pytest"],
    )
    plugin = GenericProjectPlugin(project_name="demo", repo_path=tmp_path)
    return WorkflowEngine(
        context=context,
        plugin=plugin,
        artifact_manager=ArtifactManager(context=context),
        audit_logger=AuditLogger(run_dir=context.resolved_artifact_root()),
        policy_engine=PolicyEngine(context=context),
        ticket_connector=build_ticket_connector("mock", {}),
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
        max_fix_iterations=2,
    )


def test_retry_loop_on_validation_failure(monkeypatch, tmp_path: Path) -> None:
    from sdk_agent.core import workflow_engine as engine_mod

    engine = _engine(tmp_path)

    calls = {"tests": 0}

    monkeypatch.setattr(engine_mod, "run_lint", lambda _ctx: CommandResult("lint", 0, "", ""))

    def fake_tests(_ctx):
        calls["tests"] += 1
        if calls["tests"] == 1:
            return CommandResult("tests", 1, "fail", "")
        return CommandResult("tests", 0, "ok", "")

    monkeypatch.setattr(engine_mod, "run_tests", fake_tests)

    state = asyncio.run(engine.run(flow=FlowType.FEATURE, request="Implement"))
    assert state.fix_iteration_count >= 2
    assert calls["tests"] >= 2
