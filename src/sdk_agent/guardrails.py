from __future__ import annotations

import shlex
from pathlib import Path


FORBIDDEN_SHELL_TOKENS = {
    "rm -rf /",
    "sudo",
    "shutdown",
    "reboot",
    "mkfs",
    "dd if=",
    "curl | sh",
    "wget | sh",
    "git push origin main",
}


def ensure_path_within(base: Path, candidate: Path) -> Path:
    resolved_base = base.resolve()
    resolved_candidate = candidate.resolve()
    if resolved_base == resolved_candidate or resolved_base in resolved_candidate.parents:
        return resolved_candidate
    raise ValueError(f"Path '{resolved_candidate}' is outside repository sandbox '{resolved_base}'.")


def is_command_allowed(command: str, allowlist: list[str]) -> bool:
    normalized = " ".join(command.split())
    for forbidden in FORBIDDEN_SHELL_TOKENS:
        if forbidden in normalized:
            return False

    if not allowlist:
        return False

    return any(normalized == allowed or normalized.startswith(f"{allowed} ") for allowed in allowlist)


def validate_shell_command(command: str, allowlist: list[str]) -> list[str]:
    if not command.strip():
        raise ValueError("Empty command is not allowed.")

    if not is_command_allowed(command, allowlist):
        raise PermissionError(f"Command is not allowed by guardrails: {command}")

    return shlex.split(command)


def validate_branch_name(branch_name: str) -> None:
    cleaned = branch_name.strip()
    if not cleaned:
        raise ValueError("Branch name cannot be empty.")
    if cleaned in {"main", "master", "production"}:
        raise PermissionError("Creating or switching protected branch names is not allowed in automation.")
