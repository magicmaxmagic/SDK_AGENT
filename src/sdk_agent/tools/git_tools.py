from __future__ import annotations

from sdk_agent.context import ProjectContext
from sdk_agent.guardrails import validate_branch_name
from sdk_agent.models import CommandResult
from sdk_agent.tools.shell_tools import safe_run_command


def git_status(context: ProjectContext) -> CommandResult:
    return safe_run_command(context, "git status --short")


def git_diff(context: ProjectContext) -> CommandResult:
    return safe_run_command(context, "git diff")


def git_create_branch(context: ProjectContext, branch_name: str) -> CommandResult:
    validate_branch_name(branch_name)
    return safe_run_command(context, f"git checkout -b {branch_name}")


def collect_changed_files(context: ProjectContext) -> list[str]:
    result = safe_run_command(context, "git status --short")
    files: list[str] = []
    for line in result.stdout.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        parts = cleaned.split(maxsplit=1)
        if len(parts) == 2:
            files.append(parts[1])
    return files
