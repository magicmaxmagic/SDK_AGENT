from dataclasses import dataclass

from sdk_agent.plugins.base import BaseProjectPlugin


@dataclass
class PortfolioProjectPlugin(BaseProjectPlugin):
    """Plugin profile for portfolio/frontend repositories."""

    def get_shared_tools(self) -> list:
        return ["shell", "filesystem"]

    def get_role_tools(self) -> dict[str, list]:
        return {
            "developer": ["codex"],
            "tester": ["shell"],
            "deployer": ["shell"],
        }

    def get_role_instruction_suffixes(self) -> dict[str, str]:
        return {
            "planner": "Prioritize user-facing impact and break work into incremental UI-safe milestones.",
            "developer": "Preserve UX consistency, avoid breaking existing routes, and keep diffs minimal.",
            "tester": "Validate responsive behavior and core user journeys before accepting changes.",
        }

    def get_workflow_prompt_overrides(self) -> dict[str, str]:
        return {
            "testing": (
                "Run functional checks on critical user flows, then run project test and lint commands, "
                "and report regressions with reproduction steps."
            ),
            "review": (
                "Review for regressions, accessibility concerns, performance issues, and maintainability risks."
            ),
        }