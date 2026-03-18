from __future__ import annotations

from sdk_agent.models import ReviewFinding, Severity, ValidationSummary, WorkflowState


def has_critical_findings(findings: list[ReviewFinding]) -> bool:
    return any(f.blocking or f.severity in {Severity.HIGH, Severity.CRITICAL} for f in findings)


def should_rework_from_validation(validation: ValidationSummary) -> bool:
    return not validation.passed


def should_rework_from_review(findings: list[ReviewFinding]) -> bool:
    return has_critical_findings(findings)


def can_retry(state: WorkflowState, max_iterations: int) -> bool:
    return state.fix_iteration_count < max_iterations
