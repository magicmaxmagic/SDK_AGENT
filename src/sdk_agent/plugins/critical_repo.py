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

    def required_staging_approvals(self) -> int:
        return 2

    def required_production_approvals(self) -> int:
        return 4

    def production_approval_validity_minutes(self) -> int:
        return 60

    def ticket_connector(self) -> str:
        return "servicenow"

    def ticket_connector_settings(self) -> dict[str, object]:
        return {
            "accepted_sources": ["itsm", "cab"],
            "strict_known": False,
        }
