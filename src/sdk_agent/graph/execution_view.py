from __future__ import annotations

from typing import Any

from sdk_agent.graph.models import NodeExecutionState, NodeStatus, WorkflowDefinition
from sdk_agent.models import WorkflowState


def build_execution_view(
    definition: WorkflowDefinition,
    state: WorkflowState,
    node_history: list[NodeExecutionState],
) -> dict[str, Any]:
    history_map = {item.node_id: item for item in node_history}
    nodes: list[dict[str, Any]] = []
    for node in definition.nodes:
        item = history_map.get(node.node_id)
        status = _node_status_for(node_id=node.node_id, state=state, execution=item)
        nodes.append(
            {
                "id": node.node_id,
                "label": node.label,
                "type": node.node_type.value,
                "role": node.role,
                "status": status,
                "retries": len(item.retries) if item else 0,
                "failure_reason": item.failure_reason if item else None,
                "branch_decisions": [decision.to_dict() for decision in item.branch_decisions] if item else [],
                "artifacts": item.artifacts if item else [],
            }
        )

    edges = [
        {
            "id": edge.edge_id,
            "source": edge.source,
            "target": edge.target,
            "condition": edge.condition,
            "branch_label": edge.branch_label,
            "loop": edge.loop,
        }
        for edge in definition.edges
    ]

    return {
        "run_id": state.run_id,
        "workflow": definition.to_dict(),
        "current_node_id": state.current_node_id,
        "nodes": nodes,
        "edges": edges,
        "status": state.final_status.value,
        "errors": list(state.errors),
        "pending_actions": list(state.pending_actions),
        "events": list(state.events),
    }


def _node_status_for(node_id: str, state: WorkflowState, execution: NodeExecutionState | None) -> str:
    if execution is not None:
        return execution.status.value
    if state.current_node_id == node_id and state.final_status.value == "running":
        return NodeStatus.RUNNING.value
    if state.final_status.value in {"failed", "blocked"} and state.current_node_id == node_id:
        return NodeStatus.FAILED.value if state.final_status.value == "failed" else NodeStatus.BLOCKED.value
    return NodeStatus.WAITING.value
