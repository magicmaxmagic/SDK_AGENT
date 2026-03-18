from dataclasses import dataclass
from sdk_agent.context import ProjectContext


@dataclass
class BaseProjectPlugin:
    context: ProjectContext

    def get_context(self) -> ProjectContext:
        return self.context

    def get_shared_tools(self) -> list:
        return []

    def get_role_tools(self) -> dict[str, list]:
        return {}

    def get_role_instruction_suffixes(self) -> dict[str, str]:
        return {}

    def get_workflow_prompt_overrides(self) -> dict[str, str]:
        return {}
