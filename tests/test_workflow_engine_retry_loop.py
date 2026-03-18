import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

from sdk_agent.context import ProjectContext
from sdk_agent.core.artifacts import ArtifactManager
from sdk_agent.core.workflow_engine import WorkflowEngine
from sdk_agent.models import CommandResult, FlowType, WorkflowStatus
from sdk_agent.plugins import GenericProjectPlugin


class DummyAgent:
    def __init__(self, name: str):
        self.name = name
        self.mcp_servers = []


class StubRunner:
    async def run(self, agent, prompt: str) -> str:  # noqa: ARG002
        if agent.name == "planner":
            return "Plan"
        if agent.name == "developer":
            return "Implementation"
        if agent.name == "reviewer":
            return "No blocking | low | none | false | none"
        if agent.name == "release":
            return "Release"
        return "Deploy"


@asynccontextmanager
async def fake_codex_server():
    yield object()


def _engine(tmp_path: Path) -> WorkflowEngine:
    plugin = GenericProjectPlugin(project_name="demo", repo_path=tmp_path)
    context = ProjectContext(
        project_name="demo",
        repo_path=tmp_path,
        lint_command="pytest -q",
        test_command="pytest -q",
        allowed_commands=["git status", "git diff", "git rev-parse", "git checkout -b"],
    )
    return WorkflowEngine(
        context=context,
        plugin=plugin,
        artifact_manager=ArtifactManager(context=context),
        planner=DummyAgent("planner"),
        developer=DummyAgent("developer"),
        tester=DummyAgent("tester"),
        reviewer=DummyAgent("reviewer"),
        release_manager=DummyAgent("release"),
        deployer=DummyAgent("deployer"),
        triage=DummyAgent("triage"),
        runner=StubRunner(),
        max_fix_iterations=2,
    )


def test_retry_loop_on_failed_validation(monkeypatch, tmp_path: Path) -> None:
    from sdk_agent.core import workflow_engine as engine_mod

    engine = _engine(tmp_path)

    call_count = {"tests": 0}

    def fake_tests(_ctx):
        call_count["tests"] += 1
        if call_count["tests"] == 1:
            return CommandResult(command="test", exit_code=1, stdout="failed", stderr="")
        return CommandResult(command="test", exit_code=0, stdout="ok", stderr="")

    monkeypatch.setattr(engine_mod, "codex_mcp_server", fake_codex_server)
    monkeypatch.setattr(
        engine_mod,
        "run_lint",
        lambda _ctx: CommandResult(command="lint", exit_code=0, stdout="", stderr=""),
    )
    monkeypatch.setattr(engine_mod, "run_tests", fake_tests)
    monkeypatch.setattr(engine_mod, "git_collect_changed_files", lambda _ctx: ["src/app.py"])
    monkeypatch.setattr(
        engine_mod,
        "git_diff",
        lambda _ctx: CommandResult(command="git diff", exit_code=0, stdout="diff", stderr=""),
    )
    monkeypatch.setattr(
        engine_mod,
        "prepare_git_workflow",
        lambda **_: SimpleNamespace(
            branch_name="bugfix/redirect",
            changed_files=["src/app.py"],
            commit_message="fix: redirect",
            pr_body="PR body",
        ),
    )

    state = asyncio.run(engine.run(flow=FlowType.BUGFIX, request="Fix redirect"))

    assert state.final_status == WorkflowStatus.COMPLETED
    assert state.fix_iteration_count >= 2
    assert call_count["tests"] >= 2
