from pathlib import Path

from sdk_agent.models import FlowType, WorkflowState, WorkflowStatus


def test_workflow_state_updates() -> None:
    state = WorkflowState.create(flow=FlowType.FEATURE, request="Add auth", artifacts_path=Path(".sdk_agent_runs"))
    state.implementation_plan = "Plan"
    state.accepted_plan = True
    state.changed_files = ["src/app.py"]
    state.add_event("phase:review")
    state.complete()

    assert state.accepted_plan is True
    assert state.changed_files == ["src/app.py"]
    assert state.final_status == WorkflowStatus.COMPLETED
    assert "phase:review" in state.events
