from sdk_agent.graph.builder import build_workflow_definition
from sdk_agent.graph.models import WorkflowRun
from sdk_agent.graph.serializer import serialize_definition, serialize_run
from sdk_agent.models import FlowType


def test_serialize_definition_includes_layout() -> None:
    definition = build_workflow_definition(FlowType.FEATURE)
    payload = serialize_definition(definition)

    assert payload["workflow_id"] == "flow-feature"
    assert payload["layout"]["engine"] == "grid-v1"
    assert definition.entry_node_id in payload["layout"]["positions"]


def test_serialize_run_includes_layout_and_state() -> None:
    definition = build_workflow_definition(FlowType.PLAN)
    run = WorkflowRun(run_id="run-xyz", definition=definition, current_node_id=definition.entry_node_id)

    payload = serialize_run(run)
    assert payload["run_id"] == "run-xyz"
    assert payload["layout"]["entry_node_id"] == definition.entry_node_id
