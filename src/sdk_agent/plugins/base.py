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
        return ["git status", "git diff", "pytest", "ruff check", "npm test", "npm run lint"]

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

    def to_context(self) -> ProjectContext:
        return ProjectContext(
            project_name=self.project_name,
            repo_path=self.repo_path,
            lint_command=self.lint_command(),
            test_command=self.test_command(),
            build_command=self.build_command(),
            deploy_staging_command=self.deploy_staging_command(),
            artifact_root=self.artifact_root,
            project_rules=self.project_rules(),
            allowed_commands=self.allowed_commands(),
        )
