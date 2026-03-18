from __future__ import annotations

from sdk_agent.core.policy_engine import PolicyEngine
from sdk_agent.models import ActionType, PolicyDecision, RoleName


def evaluate_policy(engine: PolicyEngine, action: ActionType, role: RoleName, file_path: str | None = None) -> PolicyDecision:
    return engine.evaluate(action=action, role=role, file_path=file_path)


def assert_policy_allowed(decision: PolicyDecision) -> None:
    if not decision.allowed:
        raise PermissionError(f"Policy denied action '{decision.action.value}': {decision.reason}")
