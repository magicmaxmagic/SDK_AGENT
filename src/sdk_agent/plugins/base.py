from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sdk_agent.context import ProjectContext


@dataclass(slots=True)
class BaseProjectPlugin:
    """Base plugin carrying project rules and deterministic tool constraints."""

    project_name: str
    repo_path: Path
    artifact_root: Path = Path(".sdk_agent_runs")

    def allowed_commands(self) -> list[str]:
        return [
            "git status",
            "git diff",
            "git rev-parse",
            "git checkout -b",
            "pytest",
            "ruff check",
            "npm test",
            "npm run lint",
            "python -m compileall",
        ]

    def lint_command(self) -> str:
        return "python -m compileall -q src tests"

    def test_command(self) -> str:
        return "pytest -q"

    def build_command(self) -> str | None:
        return None

    def deploy_staging_command(self) -> str | None:
        return None

    def project_rules(self) -> list[str]:
        return [
            "Keep diffs small and focused.",
            "Do not modify unrelated files.",
            "Never deploy to production automatically.",
        ]

    def role_capability_overrides(self) -> dict[str, dict[str, bool]]:
        return {}

    def to_context(self) -> ProjectContext:
        deploy_staging = self.deploy_staging_command()
        return ProjectContext(
            project_name=self.project_name,
            repo_path=self.repo_path,
            lint_command=self.lint_command(),
            test_command=self.test_command(),
            build_command=self.build_command(),
            deploy_staging_command=deploy_staging,
            allow_staging_deploy=bool(deploy_staging),
            artifact_root=self.artifact_root,
            project_rules=self.project_rules(),
            allowed_commands=self.allowed_commands(),
            role_capability_overrides=self.role_capability_overrides(),
        )
