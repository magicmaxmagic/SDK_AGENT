from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class ProjectContext:
    """Resolved project context used by deterministic tools and workflow phases."""

    project_name: str
    repo_path: Path
    lint_command: str
    test_command: str
    build_command: str | None = None
    deploy_staging_command: str | None = None
    artifact_root: Path = Path(".sdk_agent_runs")
    project_rules: list[str] = field(default_factory=list)
    allowed_commands: list[str] = field(default_factory=list)

    def resolved_artifact_root(self) -> Path:
        return (self.repo_path / self.artifact_root).resolve()
