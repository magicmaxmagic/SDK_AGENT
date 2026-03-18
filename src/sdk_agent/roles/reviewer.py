from __future__ import annotations

from sdk_agent.core.base_agent import BaseAgentFactory
from sdk_agent.models import ReviewFinding, Severity
from sdk_agent.plugins.base import BaseProjectPlugin


SEVERITY_MAP = {
    "low": Severity.LOW,
    "medium": Severity.MEDIUM,
    "high": Severity.HIGH,
    "critical": Severity.CRITICAL,
}


def make_reviewer_agent(
    factory: BaseAgentFactory,
    plugin: BaseProjectPlugin,
):
    context = plugin.to_context()
    instructions = (
        f"You are the Reviewer for project '{context.project_name}'. "
        "Read-only reviewer mindset: do not implement fixes directly.\n"
        "Output findings in this strict format per line:\n"
        "TITLE | SEVERITY | FILE_PATH_OR_NONE | BLOCKING(true/false) | RECOMMENDATION\n"
        "Include only concrete actionable findings."
    )
    return factory.create(
        name="Reviewer",
        instructions=instructions,
    )


def parse_review_findings(text: str) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or "|" not in line:
            continue

        parts = [part.strip() for part in line.split("|", maxsplit=4)]
        if len(parts) != 5:
            continue

        title, severity_raw, file_path_raw, blocking_raw, recommendation = parts
        severity = SEVERITY_MAP.get(severity_raw.lower(), Severity.MEDIUM)
        file_path = None if file_path_raw.lower() in {"none", "n/a", ""} else file_path_raw
        blocking = blocking_raw.lower() in {"true", "yes", "1"}

        findings.append(
            ReviewFinding(
                title=title or "Untitled finding",
                severity=severity,
                file_path=file_path,
                recommendation=recommendation,
                blocking=blocking,
                details=line,
            )
        )

    if findings:
        return findings

    normalized = text.strip() or "No review feedback generated"
    fallback_severity = Severity.CRITICAL if "critical" in normalized.lower() else Severity.MEDIUM
    fallback_blocking = fallback_severity in {Severity.HIGH, Severity.CRITICAL}
    return [
        ReviewFinding(
            title="Review summary",
            severity=fallback_severity,
            file_path=None,
            recommendation=normalized,
            blocking=fallback_blocking,
            details=normalized,
        )
    ]
