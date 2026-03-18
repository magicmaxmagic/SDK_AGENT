from sdk_agent.core.policy_engine import TRUST_POLICIES
from sdk_agent.models import TrustProfile


def test_critical_profile_is_restrictive() -> None:
    critical = TRUST_POLICIES[TrustProfile.CRITICAL]
    assert critical.allow_code_writes is False
    assert critical.allow_production_deploy is False


def test_sandbox_profile_is_more_permissive() -> None:
    sandbox = TRUST_POLICIES[TrustProfile.LOW_RISK_SANDBOX]
    assert sandbox.allow_code_writes is True
    assert sandbox.allow_pr_draft is True
