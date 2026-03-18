from dataclasses import dataclass, field


@dataclass
class RoleConfig:
    enabled: bool = True
    instructions_override: str | None = None
    instructions_suffix: str | None = None
    tools: list | None = None


@dataclass
class WorkflowConfig:
    run_planning: bool = True
    run_testing: bool = True
    run_review: bool = True
    run_deploy: bool = True
    prompt_overrides: dict[str, str] = field(default_factory=dict)


@dataclass
class TeamConfig:
    model: str | None = None
    shared_tools: list = field(default_factory=list)
    roles: dict[str, RoleConfig] = field(default_factory=dict)
    workflow: WorkflowConfig = field(default_factory=WorkflowConfig)

    def role(self, role_name: str) -> RoleConfig:
        return self.roles.get(role_name, RoleConfig())