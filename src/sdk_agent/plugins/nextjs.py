from __future__ import annotations

from sdk_agent.plugins.base import BaseProjectPlugin


class NextJsPlugin(BaseProjectPlugin):
    def allowed_commands(self) -> list[str]:
        return [
            "git status",
            "git diff",
            "npm test",
            "npm run lint",
            "npm run build",
            "npm run typecheck",
        ]

    def lint_command(self) -> str:
        return "npm run lint"

    def test_command(self) -> str:
        return "npm test"

    def build_command(self) -> str | None:
        return "npm run build"

    def deploy_staging_command(self) -> str | None:
        return "vercel --prebuilt --target preview"

    def project_rules(self) -> list[str]:
        return super().project_rules() + [
            "Preserve existing routes and UX behavior.",
            "Update tests when UI behavior changes.",
        ]
