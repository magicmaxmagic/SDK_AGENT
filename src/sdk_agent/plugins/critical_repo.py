from __future__ import annotations

from sdk_agent.models import AutonomyLevel, TrustProfile
from sdk_agent.plugins.base import BaseProjectPlugin


class CriticalRepoPlugin(BaseProjectPlugin):
    """Strict profile for critical repositories."""

    def trust_profile(self) -> TrustProfile:
        return TrustProfile.CRITICAL

    def autonomy_level(self) -> AutonomyLevel:
        return AutonomyLevel.SUGGEST

    def protected_paths(self) -> list[str]:
        return super().protected_paths() + ["auth/", "billing/", "db/migrations/"]

    def role_capability_overrides(self) -> dict[str, dict[str, bool]]:
        return {
            "developer": {"write": False},
            "tester": {"shell": True},
        }
