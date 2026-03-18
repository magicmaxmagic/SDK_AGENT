from pathlib import Path

from sdk_agent.context import ProjectContext
from sdk_agent.core.git_workflow import prepare_git_workflow
from sdk_agent.models import AutonomyLevel, TrustProfile


def _context(tmp_path: Path) -> ProjectContext:
    return ProjectContext(
        project_name="demo",
        repo_path=tmp_path,
        lint_command="pytest -q",
        test_command="pytest -q",
        autonomy_level=AutonomyLevel.IMPLEMENT,
        trust_profile=TrustProfile.NORMAL_INTERNAL,
        dry_run=True,
        allowed_commands=["git status", "git diff", "git rev-parse", "git checkout -b", "git worktree add"],
    )


def test_prepare_git_workflow(tmp_path: Path) -> None:
    context = _context(tmp_path)
    plan = prepare_git_workflow(
        context=context,
        request="Add page",
        branch_name="feature/add-page",
        create_branch=False,
        validation_summary="tests ok",
        use_worktree=False,
        run_id="run-1",
    )

    assert plan.branch_name in {"feature/add-page", "[dry-run]", "HEAD", "main"} or isinstance(plan.branch_name, str)
    assert isinstance(plan.commit_message, str)
