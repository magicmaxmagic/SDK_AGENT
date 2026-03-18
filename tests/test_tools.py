from pathlib import Path

from sdk_agent.context import ProjectContext
from sdk_agent.models import FlowType, ReviewFinding, Severity, ValidationSummary, WorkflowState
from sdk_agent.tools.artifact_tools import write_artifact
from sdk_agent.tools.file_tools import load_project_rules
from sdk_agent.core.transitions import should_rework_from_review, should_rework_from_validation


def _context(tmp_path: Path) -> ProjectContext:
    return ProjectContext(
        project_name="tmp",
        repo_path=tmp_path,
        lint_command="python -m compileall -q .",
        test_command="python -m compileall -q .",
        artifact_root=Path(".sdk_agent_runs"),
        project_rules=["Keep diffs small"],
        allowed_commands=["python -m compileall", "git status", "git diff"],
    )


def test_artifact_write(tmp_path: Path) -> None:
    context = _context(tmp_path)
    artifact = write_artifact(context, "run-1", "plan.md", "hello")

    assert artifact.exists()
    assert artifact.read_text(encoding="utf-8") == "hello"


def test_load_project_rules(tmp_path: Path) -> None:
    context = _context(tmp_path)
    assert load_project_rules(context) == ["Keep diffs small"]


def test_transition_branching() -> None:
    ok = ValidationSummary(lint=None, tests=None)
    assert should_rework_from_validation(ok) is False

    finding = ReviewFinding(title="Critical bug", details="Breaks login", severity=Severity.CRITICAL)
    assert should_rework_from_review([finding]) is True


def test_state_serialization(tmp_path: Path) -> None:
    state = WorkflowState.create(flow=FlowType.REVIEW, request="Review", artifacts_path=tmp_path)
    payload = state.to_dict()
    assert payload["flow"] == "review"
    assert "task_id" in payload
