from __future__ import annotations

import subprocess

from sdk_agent.context import ProjectContext
from sdk_agent.guardrails import validate_shell_command
from sdk_agent.logging_config import get_logger
from sdk_agent.models import CommandResult

LOGGER = get_logger("tools.shell")


def safe_run_command(context: ProjectContext, command: str, role: str | None = None) -> CommandResult:
    argv = validate_shell_command(command, context.allowed_commands, role=role)
    if context.dry_run:
        LOGGER.info(
            "command_simulated",
            extra={"extra_fields": {"command": command, "role": role, "dry_run": True}},
        )
        return CommandResult(
            command=command,
            exit_code=0,
            stdout=f"[dry-run] skipped execution: {' '.join(argv)}",
            stderr="",
        )

    completed = subprocess.run(
        argv,
        cwd=context.repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    LOGGER.info(
        "command_executed",
        extra={"extra_fields": {"command": command, "exit_code": completed.returncode, "role": role}},
    )
    return CommandResult(
        command=command,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
