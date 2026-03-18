from __future__ import annotations

from sdk_agent.plugins.base import BaseProjectPlugin


class GenericProjectPlugin(BaseProjectPlugin):
    """Generic defaults for mixed repositories."""

    def allowed_commands(self) -> list[str]:
        return super().allowed_commands() + ["python -m pytest", "python -m compileall"]
