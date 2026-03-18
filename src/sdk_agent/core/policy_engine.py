from __future__ import annotations

from dataclasses import dataclass

from sdk_agent.context import ProjectContext
from sdk_agent.models import (
    ActionType,
    AutonomyLevel,
    EnvironmentType,
    PolicyDecision,
    RoleName,
    TrustProfile,
)


AUTONOMY_ORDER: dict[AutonomyLevel, int] = {
    AutonomyLevel.OBSERVE: 0,
    AutonomyLevel.SUGGEST: 1,
    AutonomyLevel.IMPLEMENT: 2,
    AutonomyLevel.VALIDATE: 3,
    AutonomyLevel.STAGING_DEPLOY: 4,
    AutonomyLevel.PRODUCTION_CANDIDATE: 5,
    AutonomyLevel.FULLY_AUTONOMOUS: 6,
}


@dataclass(slots=True)
class TrustProfilePolicy:
    max_autonomy: AutonomyLevel
    allow_code_writes: bool
    allow_commit: bool
    allow_pr_draft: bool
    allow_staging_deploy: bool
    allow_production_deploy: bool
    require_human_approval: bool
    allow_hotfix_mode: bool


TRUST_POLICIES: dict[TrustProfile, TrustProfilePolicy] = {
    TrustProfile.LOW_RISK_SANDBOX: TrustProfilePolicy(
        max_autonomy=AutonomyLevel.FULLY_AUTONOMOUS,
        allow_code_writes=True,
        allow_commit=True,
        allow_pr_draft=True,
        allow_staging_deploy=True,
        allow_production_deploy=False,
        require_human_approval=False,
        allow_hotfix_mode=True,
    ),
    TrustProfile.NORMAL_INTERNAL: TrustProfilePolicy(
        max_autonomy=AutonomyLevel.STAGING_DEPLOY,
        allow_code_writes=True,
        allow_commit=True,
        allow_pr_draft=True,
        allow_staging_deploy=True,
        allow_production_deploy=False,
        require_human_approval=True,
        allow_hotfix_mode=True,
    ),
    TrustProfile.SENSITIVE: TrustProfilePolicy(
        max_autonomy=AutonomyLevel.VALIDATE,
        allow_code_writes=True,
        allow_commit=False,
        allow_pr_draft=True,
        allow_staging_deploy=False,
        allow_production_deploy=False,
        require_human_approval=True,
        allow_hotfix_mode=False,
    ),
    TrustProfile.CRITICAL: TrustProfilePolicy(
        max_autonomy=AutonomyLevel.SUGGEST,
        allow_code_writes=False,
        allow_commit=False,
        allow_pr_draft=False,
        allow_staging_deploy=False,
        allow_production_deploy=False,
        require_human_approval=True,
        allow_hotfix_mode=False,
    ),
}


class PolicyEngine:
    """Central policy decision point for every critical action."""

    def __init__(self, context: ProjectContext):
        self.context = context

    def evaluate(
        self,
        action: ActionType,
        role: RoleName,
        file_path: str | None = None,
        branch_target: str | None = None,
    ) -> PolicyDecision:
        profile_policy = TRUST_POLICIES[self.context.trust_profile]

        if AUTONOMY_ORDER[self.context.autonomy_level] > AUTONOMY_ORDER[profile_policy.max_autonomy]:
            return PolicyDecision(False, "autonomy level exceeds trust profile policy", action, role)

        if action == ActionType.PUSH:
            return PolicyDecision(False, "push is never automated", action, role)

        if action == ActionType.DEPLOY_PRODUCTION:
            if not profile_policy.allow_production_deploy or not self.context.allow_production_deploy:
                return PolicyDecision(False, "production deploy is disabled by policy", action, role)
            if self.context.environment == EnvironmentType.PRODUCTION:
                return PolicyDecision(True, "production deploy allowed in production environment", action, role)
            return PolicyDecision(False, "production deploy requires production environment", action, role)

        if action == ActionType.DEPLOY_STAGING:
            if not profile_policy.allow_staging_deploy or not self.context.allow_staging_deploy:
                return PolicyDecision(False, "staging deploy not allowed by profile", action, role)

        if action in {ActionType.EDIT_FILE, ActionType.RUN_MIGRATIONS, ActionType.CHANGE_CICD, ActionType.TOUCH_SECRETS}:
            if not profile_policy.allow_code_writes:
                return PolicyDecision(False, "code writes not allowed for this trust profile", action, role)
            if file_path and self._is_protected_path(file_path):
                return PolicyDecision(False, f"path '{file_path}' is protected", action, role)

        if action == ActionType.COMMIT and not profile_policy.allow_commit:
            return PolicyDecision(False, "commit not allowed for this trust profile", action, role)

        if action == ActionType.CREATE_PR_DRAFT and not profile_policy.allow_pr_draft:
            return PolicyDecision(False, "PR draft not allowed for this trust profile", action, role)

        if action in {ActionType.CREATE_BRANCH, ActionType.CREATE_WORKTREE} and branch_target:
            if branch_target in {"main", "master", "production"}:
                return PolicyDecision(False, "protected branches are denied", action, role)

        return PolicyDecision(True, "allowed", action, role)

    def required_human_approval(self) -> bool:
        return TRUST_POLICIES[self.context.trust_profile].require_human_approval

    def _is_protected_path(self, file_path: str) -> bool:
        normalized = file_path.replace("\\", "/")
        return any(normalized.startswith(prefix) for prefix in self.context.protected_paths)
