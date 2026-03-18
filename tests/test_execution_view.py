from pathlib import Path

from sdk_agent.graph.builder import build_workflow_definition
from sdk_agent.graph.execution_view import build_execution_view
from sdk_agent.graph.models import NodeExecutionState, NodeStatus
from sdk_agent.models import AutonomyLevel, FlowType, TrustProfile, WorkflowStatus, WorkflowState


def test_execution_view_marks_node_status_from_history(tmp_path: Path) -> None:
    definition = build_workflow_definition(FlowType.PLAN)
    state = WorkflowState.create(
        flow=FlowType.PLAN,
        request="Plan",
        artifacts_path=tmp_path,
        autonomy_level=AutonomyLevel.IMPLEMENT,
        trust_profile=TrustProfile.NORMAL_INTERNAL,
    )
    state.current_node_id = "done"
    state.final_status = WorkflowStatus.RUNNING

    node_history = [NodeExecutionState(node_id="plan", status=NodeStatus.COMPLETED)]
    payload = build_execution_view(definition=definition, state=state, node_history=node_history)

    nodes = {item["id"]: item for item in payload["nodes"]}
    assert nodes["plan"]["status"] == "completed"
    assert nodes["done"]["status"] == "running"


def test_execution_view_failed_current_node(tmp_path: Path) -> None:
    definition = build_workflow_definition(FlowType.REVIEW)
    state = WorkflowState.create(
        flow=FlowType.REVIEW,
        request="Review",
        artifacts_path=tmp_path,
        autonomy_level=AutonomyLevel.IMPLEMENT,
        trust_profile=TrustProfile.NORMAL_INTERNAL,
    )
    state.current_node_id = "review"
    state.final_status = WorkflowStatus.FAILED

    payload = build_execution_view(definition=definition, state=state, node_history=[])
    nodes = {item["id"]: item for item in payload["nodes"]}
    assert nodes["review"]["status"] == "failed"
