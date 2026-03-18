from dataclasses import dataclass

from sdk_agent.plugins.base import BaseProjectPlugin


@dataclass
class BackendProjectPlugin(BaseProjectPlugin):
    """Plugin profile for backend repositories (FastAPI or Django)."""

    framework: str = "fastapi"

    def _framework_name(self) -> str:
        framework = self.framework.strip().lower()
        if framework not in {"fastapi", "django"}:
            raise ValueError("framework must be either 'fastapi' or 'django'")
        return framework

    def get_shared_tools(self) -> list:
        return ["shell", "filesystem"]

    def get_role_tools(self) -> dict[str, list]:
        return {
            "developer": ["codex", "shell"],
            "tester": ["shell"],
            "deployer": ["shell"],
        }

    def get_role_instruction_suffixes(self) -> dict[str, str]:
        framework = self._framework_name()

        if framework == "fastapi":
            backend_focus = (
                "Target FastAPI conventions: explicit request/response models, dependency-injected services, "
                "and clear API error handling."
            )
        else:
            backend_focus = (
                "Target Django conventions: keep business logic out of views, preserve migration safety, "
                "and keep app boundaries clear."
            )

        return {
            "planner": "Prioritize backward-compatible API evolution and explicit rollout steps.",
            "developer": backend_focus,
            "tester": "Add tests for happy path, edge cases, and failure scenarios for API contracts.",
            "reviewer": "Inspect schema changes, data integrity risks, and backward compatibility concerns.",
            "deployer": "Document migration, rollback, and post-deploy smoke checks before release.",
        }

    def get_workflow_prompt_overrides(self) -> dict[str, str]:
        framework = self._framework_name()

        if framework == "fastapi":
            test_hint = "Focus on endpoint behavior, validation errors, and response contracts."
        else:
            test_hint = "Focus on views, ORM queries, migrations, and admin/business workflows."

        return {
            "testing": (
                "Run backend tests and linting, report failures with root cause and minimal safe fix plan. "
                f"{test_hint}"
            ),
            "deploy": (
                "Prepare deployment sequence including DB migration plan, rollback steps, and service health checks."
            ),
        }