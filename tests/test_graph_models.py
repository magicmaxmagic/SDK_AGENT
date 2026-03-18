from sdk_agent.graph.models import NodeExecutionState, NodeStatus, NodeType, WorkflowDefinition, WorkflowEdge, WorkflowNode, WorkflowRun


def test_workflow_definition_and_run_to_dict() -> None:
    node = WorkflowNode(node_id="plan", label="Plan", node_type=NodeType.TASK, role="planner")
    done = WorkflowNode(node_id="done", label="Done", node_type=NodeType.TERMINAL)
    edge = WorkflowEdge(edge_id="e1", source="plan", target="done")
    definition = WorkflowDefinition(
        workflow_id="flow-plan",
        name="plan-workflow",
        version="v3",
        nodes=[node, done],
        edges=[edge],
        entry_node_id="plan",
    )

    run = WorkflowRun(
        run_id="run-123",
        definition=definition,
        current_node_id="done",
        node_states=[NodeExecutionState(node_id="plan", status=NodeStatus.COMPLETED)],
        status="completed",
    )

    payload = run.to_dict()
    assert payload["definition"]["entry_node_id"] == "plan"
    assert payload["definition"]["nodes"][0]["node_type"] == "task"
    assert payload["node_states"][0]["status"] == "completed"
