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
    "git push",
    "git reset --hard",
    "git checkout --",
    "mkfs",
    "chmod -R 777 /",
}


ROLE_FORBIDDEN_TOKENS = {
    "planner": {"git checkout", "git commit"},
    "reviewer": {"git checkout", "git commit", "npm", "pytest", "ruff"},
    "release_manager": {"git checkout", "git commit", "npm", "pytest", "ruff"},
    "deployer": {"git push", "kubectl apply", "helm upgrade"},
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


def validate_shell_command(command: str, allowlist: list[str], role: str | None = None) -> list[str]:
    if not command.strip():
        raise ValueError("Empty command is not allowed.")

    normalized = " ".join(command.split())

    if role:
        for forbidden in ROLE_FORBIDDEN_TOKENS.get(role, set()):
            if forbidden in normalized:
                raise PermissionError(f"Role '{role}' cannot execute command: {command}")

    if not is_command_allowed(command, allowlist):
        raise PermissionError(f"Command is not allowed by guardrails: {command}")

    return shlex.split(command)


def validate_branch_name(branch_name: str) -> None:
    cleaned = branch_name.strip()
    if not cleaned:
        raise ValueError("Branch name cannot be empty.")
    if cleaned in {"main", "master", "production"}:
        raise PermissionError("Creating or switching protected branch names is not allowed in automation.")
