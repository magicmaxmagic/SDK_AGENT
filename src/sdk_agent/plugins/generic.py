from __future__ import annotations

from sdk_agent.models import AutonomyLevel, TrustProfile
from sdk_agent.plugins.base import BaseProjectPlugin


class GenericProjectPlugin(BaseProjectPlugin):
    """Generic defaults for mixed repositories."""

    def trust_profile(self) -> TrustProfile:
        return TrustProfile.NORMAL_INTERNAL

    def autonomy_level(self) -> AutonomyLevel:
        return AutonomyLevel.IMPLEMENT

    def allowed_commands(self) -> list[str]:
        return super().allowed_commands() + ["python -m pytest", "python -m compileall"]
