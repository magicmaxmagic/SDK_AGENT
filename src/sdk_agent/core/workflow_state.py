from __future__ import annotations

from dataclasses import dataclass

from sdk_agent.models import WorkflowState


@dataclass(slots=True)
class WorkflowStateStore:
    """Explicit mutation wrapper for workflow state transitions."""

    state: WorkflowState

    def mark_phase(self, phase: str) -> None:
        self.state.current_phase = phase
        self.state.add_event(f"phase:{phase}")

    def set_plan(self, plan: str) -> None:
        self.state.implementation_plan = plan
        self.state.accepted_plan = bool(plan.strip())

    def set_changed_files(self, changed_files: list[str]) -> None:
        self.state.changed_files = changed_files

    def set_release_notes(self, notes: str) -> None:
        self.state.release_notes = notes

    def set_deploy_plan(self, deploy_plan: str) -> None:
        self.state.deploy_plan = deploy_plan

    def set_fix_iteration_reason(self, reason: str) -> None:
        self.state.fix_iteration_reason = reason

    def require_human_approval(self, required: bool) -> None:
        self.state.human_approval_required = required
