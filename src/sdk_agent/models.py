from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4


class FlowType(str, Enum):
    FEATURE = "feature"
    BUGFIX = "bugfix"
    PLAN = "plan"
    VALIDATE = "validate"
    REVIEW = "review"


class WorkflowStatus(str, Enum):
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(slots=True)
class CommandResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str


@dataclass(slots=True)
class ReviewFinding:
    title: str
    severity: Severity = Severity.MEDIUM
    file_path: str | None = None
    recommendation: str = ""
    blocking: bool = False
    details: str = ""


@dataclass(slots=True)
class ValidationRecord:
    timestamp: datetime
    lint: CommandResult | None
    tests: CommandResult | None
    passed: bool


@dataclass(slots=True)
class ReviewRecord:
    timestamp: datetime
    findings: list[ReviewFinding]
    blocking_count: int


@dataclass(slots=True)
class ValidationSummary:
    lint: CommandResult | None = None
    tests: CommandResult | None = None

    @property
    def passed(self) -> bool:
        lint_ok = self.lint is None or self.lint.exit_code == 0
        tests_ok = self.tests is None or self.tests.exit_code == 0
        return lint_ok and tests_ok


@dataclass(slots=True)
class WorkflowState:
    task_id: str
    workflow_kind: FlowType
    branch_name: str | None
    original_request: str
    artifacts_path: Path
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    implementation_plan: str | None = None
    accepted_plan: bool = False
    changed_files: list[str] = field(default_factory=list)
    lint_result: CommandResult | None = None
    test_result: CommandResult | None = None
    validation_history: list[ValidationRecord] = field(default_factory=list)
    review_findings: list[ReviewFinding] = field(default_factory=list)
    review_history: list[ReviewRecord] = field(default_factory=list)
    release_notes: str | None = None
    deploy_plan: str | None = None
    fix_iteration_count: int = 0
    fix_iteration_reason: str | None = None
    final_status: WorkflowStatus = WorkflowStatus.RUNNING
    final_decision: str | None = None
    human_approval_required: bool = True
    errors: list[str] = field(default_factory=list)
    events: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        flow: FlowType,
        request: str,
        artifacts_path: Path,
        branch_name: str | None = None,
    ) -> "WorkflowState":
        return cls(
            task_id=f"run-{uuid4().hex[:10]}",
            workflow_kind=flow,
            branch_name=branch_name,
            original_request=request,
            artifacts_path=artifacts_path,
        )

    def add_event(self, event: str) -> None:
        self.events.append(event)

    def add_error(self, error: str) -> None:
        self.errors.append(error)

    def fail(self, reason: str) -> None:
        self.final_status = WorkflowStatus.FAILED
        self.final_decision = "failed"
        self.add_error(reason)

    def complete(self) -> None:
        self.final_status = WorkflowStatus.COMPLETED
        self.final_decision = "completed"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["started_at"] = self.started_at.isoformat()
        payload["workflow_kind"] = self.workflow_kind.value
        payload["final_status"] = self.final_status.value
        payload["artifacts_path"] = str(self.artifacts_path)
        payload["validation_history"] = [
            {
                "timestamp": item.timestamp.isoformat(),
                "lint": _command_result_to_dict(item.lint),
                "tests": _command_result_to_dict(item.tests),
                "passed": item.passed,
            }
            for item in self.validation_history
        ]
        payload["review_history"] = [
            {
                "timestamp": item.timestamp.isoformat(),
                "blocking_count": item.blocking_count,
                "findings": [
                    {
                        "title": finding.title,
                        "severity": finding.severity.value,
                        "file_path": finding.file_path,
                        "recommendation": finding.recommendation,
                        "blocking": finding.blocking,
                        "details": finding.details,
                    }
                    for finding in item.findings
                ],
            }
            for item in self.review_history
        ]
        return payload


def _command_result_to_dict(result: CommandResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "command": result.command,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
