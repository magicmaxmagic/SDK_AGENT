import pytest

from sdk_agent.guardrails import validate_shell_command


def test_guardrails_reject_forbidden() -> None:
    with pytest.raises(PermissionError):
        validate_shell_command("rm -rf /", ["pytest"])


def test_guardrails_reject_not_allowlisted() -> None:
    with pytest.raises(PermissionError):
        validate_shell_command("git push origin main", ["git status", "git diff"])


def test_guardrails_accept_allowlisted() -> None:
    argv = validate_shell_command("git status --short", ["git status", "git diff"])
    assert argv[0] == "git"
