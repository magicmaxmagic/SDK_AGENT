from dataclasses import dataclass, field


@dataclass
class ProjectContext:
    project_name: str
    repo_path: str
    test_command: str = "pytest"
    lint_command: str = "ruff check ."
    deploy_staging_command: str | None = None
    deploy_production_command: str | None = None
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
