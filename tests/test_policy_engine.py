from pathlib import Path

from sdk_agent.context import ProjectContext
from sdk_agent.core.policy_engine import PolicyEngine
from sdk_agent.models import ActionType, AutonomyLevel, RoleName, TrustProfile


def _context(trust: TrustProfile, autonomy: AutonomyLevel) -> ProjectContext:
    return ProjectContext(
        project_name="demo",
        repo_path=Path("."),
        lint_command="pytest -q",
        test_command="pytest -q",
        trust_profile=trust,
        autonomy_level=autonomy,
        allowed_commands=["git status", "git diff", "pytest"],
    )


def test_policy_denies_excessive_autonomy() -> None:
    engine = PolicyEngine(_context(TrustProfile.CRITICAL, AutonomyLevel.FULLY_AUTONOMOUS))
    decision = engine.evaluate(ActionType.EDIT_FILE, RoleName.DEVELOPER)
    assert decision.allowed is False


def test_policy_denies_push() -> None:
    engine = PolicyEngine(_context(TrustProfile.NORMAL_INTERNAL, AutonomyLevel.IMPLEMENT))
    decision = engine.evaluate(ActionType.PUSH, RoleName.DEVELOPER)
    assert decision.allowed is False


def test_policy_allows_branch_create() -> None:
    engine = PolicyEngine(_context(TrustProfile.NORMAL_INTERNAL, AutonomyLevel.IMPLEMENT))
    decision = engine.evaluate(ActionType.CREATE_BRANCH, RoleName.DEVELOPER, branch_target="feature/test")
    assert decision.allowed is True
