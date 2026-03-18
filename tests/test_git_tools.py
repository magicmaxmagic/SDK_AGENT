from pathlib import Path

from sdk_agent.context import ProjectContext
from sdk_agent.models import CommandResult
from sdk_agent.tools import git_tools


def _context(tmp_path: Path) -> ProjectContext:
    return ProjectContext(
        project_name="demo",
        repo_path=tmp_path,
        lint_command="pytest -q",
        test_command="pytest -q",
        allowed_commands=["git status", "git diff", "git checkout -b", "git rev-parse"],
    )


def test_git_prepare_helpers() -> None:
    msg = git_tools.git_prepare_commit_message("Add login fix", ["app/auth.py"])
    body = git_tools.git_prepare_pr_body("Add login fix", ["app/auth.py"], "tests=0")
    assert "Add login fix" in msg
    assert "app/auth.py" in body


def test_git_collect_changed_files(monkeypatch, tmp_path: Path) -> None:
    context = _context(tmp_path)

    def fake_run(_context, command: str, role: str | None = None):
        return CommandResult(command=command, exit_code=0, stdout=" M app.py\n?? tests/test_app.py\n", stderr="")

    monkeypatch.setattr(git_tools, "safe_run_command", fake_run)
    files = git_tools.git_collect_changed_files(context)
    assert files == ["app.py", "tests/test_app.py"]
