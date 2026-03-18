from __future__ import annotations

from typing import Any

from sdk_agent.models import WorkflowState


def build_run_payload(state: WorkflowState, *, execution_history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    payload = state.to_dict()
    payload["execution_history"] = list(execution_history or [])
    payload["summary"] = {
        "run_id": state.run_id,
        "status": state.final_status.value,
        "current_node_id": state.current_node_id,
        "errors": len(state.errors),
        "retries": state.fix_iteration_count,
    }
    return payload
