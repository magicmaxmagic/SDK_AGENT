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
    details: str
    severity: Severity = Severity.MEDIUM
    file_path: str | None = None


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
    flow: FlowType
    original_request: str
    artifacts_path: Path
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    implementation_plan: str | None = None
    accepted_plan: bool = False
    changed_files: list[str] = field(default_factory=list)
    lint_result: CommandResult | None = None
    test_result: CommandResult | None = None
    review_findings: list[ReviewFinding] = field(default_factory=list)
    release_notes: str | None = None
    deploy_plan: str | None = None
    final_status: WorkflowStatus = WorkflowStatus.RUNNING
    errors: list[str] = field(default_factory=list)
    iteration: int = 0
    events: list[str] = field(default_factory=list)

    @classmethod
    def create(cls, flow: FlowType, request: str, artifacts_path: Path) -> "WorkflowState":
        return cls(
            task_id=f"run-{uuid4().hex[:10]}",
            flow=flow,
            original_request=request,
            artifacts_path=artifacts_path,
        )

    def add_event(self, event: str) -> None:
        self.events.append(event)

    def add_error(self, error: str) -> None:
        self.errors.append(error)

    def fail(self, reason: str) -> None:
        self.final_status = WorkflowStatus.FAILED
        self.add_error(reason)

    def complete(self) -> None:
        self.final_status = WorkflowStatus.COMPLETED

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["started_at"] = self.started_at.isoformat()
        payload["flow"] = self.flow.value
        payload["final_status"] = self.final_status.value
        payload["artifacts_path"] = str(self.artifacts_path)
        return payload
