from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sdk_agent.context import ProjectContext
from sdk_agent.models import AutonomyLevel, EnvironmentType, RoleName, TrustProfile


@dataclass(slots=True)
class BaseProjectPlugin:
    """Base plugin for repository-specific policy and execution controls."""

    project_name: str
    repo_path: Path
    artifact_root: Path = Path(".sdk_agent_runs")

    def trust_profile(self) -> TrustProfile:
        return TrustProfile.NORMAL_INTERNAL

    def autonomy_level(self) -> AutonomyLevel:
        return AutonomyLevel.SUGGEST

    def environment(self) -> EnvironmentType:
        return EnvironmentType.LOCAL

    def allowed_commands(self) -> list[str]:
        return [
            "git status",
            "git diff",
            "git rev-parse",
            "git checkout -b",
            "git worktree add",
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

    def deploy_production_command(self) -> str | None:
        return None

    def rollback_staging_command(self) -> str | None:
        return None

    def rollback_production_command(self) -> str | None:
        return None

    def protected_paths(self) -> list[str]:
        return [".github/workflows", "infra/", "secrets/"]

    def project_rules(self) -> list[str]:
        return [
            "Keep diffs small and focused.",
            "Do not modify unrelated files.",
            "Never deploy to production automatically.",
            "Never push automatically.",
        ]

    def role_capability_overrides(self) -> dict[str, dict[str, bool]]:
        return {}

    def role_mcp_access(self) -> dict[RoleName, bool]:
        return {
            RoleName.DEVELOPER: True,
            RoleName.TESTER: False,
            RoleName.PLANNER: False,
            RoleName.REVIEWER: False,
            RoleName.SECURITY_REVIEWER: False,
        }

    def to_context(self) -> ProjectContext:
        allowed_commands = list(self.allowed_commands())
        for command in (
            self.deploy_staging_command(),
            self.deploy_production_command(),
            self.rollback_staging_command(),
            self.rollback_production_command(),
        ):
            if command and command not in allowed_commands:
                allowed_commands.append(command)

        return ProjectContext(
            project_name=self.project_name,
            repo_path=self.repo_path,
            lint_command=self.lint_command(),
            test_command=self.test_command(),
            build_command=self.build_command(),
            deploy_staging_command=self.deploy_staging_command(),
            deploy_production_command=self.deploy_production_command(),
            rollback_staging_command=self.rollback_staging_command(),
            rollback_production_command=self.rollback_production_command(),
            allow_staging_deploy=bool(self.deploy_staging_command()),
            allow_production_deploy=False,
            artifact_root=self.artifact_root,
            project_rules=self.project_rules(),
            allowed_commands=allowed_commands,
            protected_paths=self.protected_paths(),
            role_capability_overrides=self.role_capability_overrides(),
            trust_profile=self.trust_profile(),
            autonomy_level=self.autonomy_level(),
            environment=self.environment(),
        )
