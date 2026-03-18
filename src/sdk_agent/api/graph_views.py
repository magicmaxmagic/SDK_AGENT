from __future__ import annotations

from typing import Any

from sdk_agent.graph.layout import compute_layout
from sdk_agent.graph.serializer import serialize_definition
from sdk_agent.models import WorkflowState


def build_graph_payload(definition: dict[str, Any], state: WorkflowState | None = None) -> dict[str, Any]:
    payload = dict(definition)
    if "layout" not in payload and all(item in payload for item in ("nodes", "edges", "entry_node_id")):
        payload["layout"] = {
            "engine": "grid-v1",
            "positions": {},
            "entry_node_id": payload.get("entry_node_id"),
        }
    if state is not None:
        payload["run_id"] = state.run_id
        payload["current_node_id"] = state.current_node_id
        payload["final_status"] = state.final_status.value
    return payload
