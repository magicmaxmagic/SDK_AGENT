from __future__ import annotations

from sdk_agent.models import AutonomyLevel, TrustProfile
from sdk_agent.plugins.base import BaseProjectPlugin


class PythonAppPlugin(BaseProjectPlugin):
    def trust_profile(self) -> TrustProfile:
        return TrustProfile.NORMAL_INTERNAL

    def autonomy_level(self) -> AutonomyLevel:
        return AutonomyLevel.VALIDATE

    def role_capability_overrides(self) -> dict[str, dict[str, bool]]:
        return {"tester": {"mcp": False}}

    def allowed_commands(self) -> list[str]:
        return [
            "git status",
            "git diff",
            "git rev-parse",
            "git checkout -b",
            "git worktree add",
            "pytest",
            "ruff check",
            "python -m compileall",
            "python -m pytest",
        ]

    def lint_command(self) -> str:
        return "ruff check ."

    def test_command(self) -> str:
        return "pytest -q"

    def build_command(self) -> str | None:
        return "python -m compileall -q src"

    def deploy_staging_command(self) -> str | None:
        return "./scripts/deploy_staging.sh"

    def project_rules(self) -> list[str]:
        return super().project_rules() + [
            "Keep static typing clean.",
            "Prefer deterministic tests over snapshot-only tests.",
        ]
