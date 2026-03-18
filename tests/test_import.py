from pathlib import Path

from sdk_agent import FlowType, WorkflowState
from sdk_agent.plugins import GenericProjectPlugin


def test_imports_and_public_models() -> None:
    plugin = GenericProjectPlugin(project_name="demo", repo_path=Path("."))
    context = plugin.to_context()

    state = WorkflowState.create(
        flow=FlowType.PLAN,
        request="Create rollout plan",
        artifacts_path=context.resolved_artifact_root(),
    )

    assert state.flow == FlowType.PLAN
    assert state.original_request == "Create rollout plan"
