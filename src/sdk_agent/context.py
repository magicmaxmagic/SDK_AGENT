from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from sdk_agent.models import AutonomyLevel, EnvironmentType, TrustProfile


@dataclass(slots=True)
class ProjectContext:
    """Resolved project context for policy-aware workflow execution."""

    project_name: str
    repo_path: Path
    lint_command: str
    test_command: str
    build_command: str | None = None
    deploy_staging_command: str | None = None
    deploy_production_command: str | None = None
    allow_staging_deploy: bool = False
    allow_production_deploy: bool = False
    dry_run: bool = False
    artifact_root: Path = Path(".sdk_agent_runs")
    project_rules: list[str] = field(default_factory=list)
    allowed_commands: list[str] = field(default_factory=list)
    protected_paths: list[str] = field(default_factory=list)
    role_capability_overrides: dict[str, dict[str, bool]] = field(default_factory=dict)
    trust_profile: TrustProfile = TrustProfile.NORMAL_INTERNAL
    autonomy_level: AutonomyLevel = AutonomyLevel.SUGGEST
    environment: EnvironmentType = EnvironmentType.LOCAL
    use_worktree: bool = False

    def resolved_artifact_root(self) -> Path:
        return (self.repo_path / self.artifact_root).resolve()
