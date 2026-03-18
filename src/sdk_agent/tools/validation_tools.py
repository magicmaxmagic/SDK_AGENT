from __future__ import annotations

from sdk_agent.context import ProjectContext
from sdk_agent.models import CommandResult
from sdk_agent.tools.shell_tools import safe_run_command


def run_lint(context: ProjectContext) -> CommandResult:
    return safe_run_command(context, context.lint_command)


def run_tests(context: ProjectContext) -> CommandResult:
    return safe_run_command(context, context.test_command)
