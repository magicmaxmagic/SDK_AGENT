from __future__ import annotations

from pathlib import Path

from sdk_agent.context import ProjectContext
from sdk_agent.guardrails import validate_branch_name
from sdk_agent.models import CommandResult
from sdk_agent.tools.shell_tools import safe_run_command


def git_status(context: ProjectContext) -> CommandResult:
    return safe_run_command(context, "git status --short", role="reviewer")


def git_diff(context: ProjectContext) -> CommandResult:
    return safe_run_command(context, "git diff", role="reviewer")


def git_current_branch(context: ProjectContext) -> CommandResult:
    return safe_run_command(context, "git rev-parse --abbrev-ref HEAD", role="reviewer")


def git_create_branch(context: ProjectContext, branch_name: str) -> CommandResult:
    validate_branch_name(branch_name)
    return safe_run_command(context, f"git checkout -b {branch_name}", role="developer")


def git_create_worktree(context: ProjectContext, branch_name: str, worktree_path: Path) -> CommandResult:
    validate_branch_name(branch_name)
    return safe_run_command(
        context,
        f"git worktree add {str(worktree_path)} {branch_name}",
        role="developer",
    )


def git_collect_changed_files(context: ProjectContext) -> list[str]:
    result = safe_run_command(context, "git status --short", role="reviewer")
    files: list[str] = []
    for line in result.stdout.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        parts = cleaned.split(maxsplit=1)
        if len(parts) == 2:
            files.append(parts[1])
    return files


def collect_changed_files(context: ProjectContext) -> list[str]:
    return git_collect_changed_files(context)


def git_prepare_commit_message(request: str, changed_files: list[str]) -> str:
    scope = changed_files[0] if changed_files else "repo"
    return f"chore({scope}): {request[:72]}"


def git_prepare_pr_body(request: str, changed_files: list[str], validation_summary: str) -> str:
    lines = [
        "## Summary",
        request,
        "",
        "## Changed Files",
    ]
    lines.extend(f"- {item}" for item in changed_files or ["- none"])
    lines.extend(["", "## Validation", validation_summary])
    return "\n".join(lines)


def git_archive_patch(context: ProjectContext, target_path: Path) -> CommandResult:
    diff_result = git_diff(context)
    target_path.write_text(diff_result.stdout, encoding="utf-8")
    return CommandResult(
        command=f"archive patch -> {target_path}",
        exit_code=diff_result.exit_code,
        stdout=str(target_path),
        stderr=diff_result.stderr,
    )
