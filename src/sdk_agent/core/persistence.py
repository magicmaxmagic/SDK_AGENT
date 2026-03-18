from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sdk_agent.models import (
    AutonomyLevel,
    FlowType,
    TrustProfile,
    WorkflowState,
    WorkflowStatus,
)


@dataclass(slots=True)
class StatePersistence:
    run_dir: Path

    @property
    def state_file(self) -> Path:
        return self.run_dir / "state.json"

    def save(self, state: WorkflowState) -> Path:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(state.to_dict(), indent=2, ensure_ascii=True), encoding="utf-8")
        return self.state_file

    def load(self) -> WorkflowState:
        payload = json.loads(self.state_file.read_text(encoding="utf-8"))
        state = WorkflowState.create(
            flow=FlowType(payload["workflow_kind"]),
            request=payload["original_request"],
            artifacts_path=Path(payload["artifacts_path"]),
            autonomy_level=AutonomyLevel(payload["autonomy_level"]),
            trust_profile=TrustProfile(payload["trust_profile"]),
            branch_name=payload.get("branch_name"),
            worktree_path=payload.get("worktree_path"),
        )
        state.run_id = payload["run_id"]
        state.task_id = payload.get("task_id")
        state.repo_path = payload.get("repo_path")
        state.project_name = payload.get("project_name")
        state.current_phase = payload.get("current_phase", "resumed")
        state.current_node_id = payload.get("current_node_id")
        state.final_status = WorkflowStatus(payload.get("final_status", "running"))
        state.changed_files = payload.get("changed_files", [])
        state.events = payload.get("events", [])
        state.errors = payload.get("errors", [])
        state.final_decision = payload.get("final_decision")
        state.human_approval_required = payload.get("human_approval_required", True)
        state.fix_iteration_count = payload.get("fix_iteration_count", 0)
        state.fix_iteration_reason = payload.get("fix_iteration_reason")
        state.release_notes = payload.get("release_notes")
        state.deploy_plan = payload.get("deploy_plan")
        state.rollback_plan = payload.get("rollback_plan")
        state.production_approval = payload.get("production_approval")
        state.production_approvals = payload.get("production_approvals", [])
        state.deployment_approvals = payload.get("deployment_approvals", [])
        state.required_staging_approvals = payload.get("required_staging_approvals", 2)
        state.required_production_approvals = payload.get("required_production_approvals", 3)
        state.production_approval_validity_minutes = payload.get("production_approval_validity_minutes", 120)
        state.deployment_history = payload.get("deployment_history", [])
        state.rollback_history = payload.get("rollback_history", [])
        state.retry_counters = payload.get("retry_counters", {})
        state.execution_history = payload.get("execution_history", [])
        return state


def locate_run_dir(artifact_root: Path, run_id: str) -> Path:
    return artifact_root / run_id
