from __future__ import annotations

from sdk_agent.graph.models import NodeType, WorkflowDefinition, WorkflowEdge, WorkflowNode
from sdk_agent.models import FlowType


def build_workflow_definition(flow: FlowType, *, version: str = "v3") -> WorkflowDefinition:
    if flow in {FlowType.FEATURE, FlowType.BUGFIX}:
        return _feature_like_definition(flow, version=version)
    if flow == FlowType.PLAN:
        return _simple_definition(flow, ["plan", "done"], version=version)
    if flow == FlowType.VALIDATE:
        return _simple_definition(flow, ["validate", "review", "done"], version=version)
    if flow == FlowType.REVIEW:
        return _simple_definition(flow, ["review", "release_notes", "done"], version=version)
    return _simple_definition(flow, ["start", "done"], version=version)


def _feature_like_definition(flow: FlowType, *, version: str) -> WorkflowDefinition:
    nodes = [
        WorkflowNode("triage", "Triage", NodeType.TASK, role="triage"),
        WorkflowNode("plan", "Plan", NodeType.TASK, role="planner"),
        WorkflowNode("architecture", "Architecture", NodeType.TASK, role="architect"),
        WorkflowNode("implementation", "Implementation", NodeType.TASK, role="developer"),
        WorkflowNode("validation", "Validation", NodeType.TASK, role="tester"),
        WorkflowNode("review", "Review", NodeType.TASK, role="reviewer"),
        WorkflowNode("security_gate", "Security Gate", NodeType.GATE, role="policy_enforcer"),
        WorkflowNode("security_review", "Security Review", NodeType.TASK, role="security_reviewer"),
        WorkflowNode("approval_gate", "Approval Gate", NodeType.APPROVAL, role="policy_enforcer"),
        WorkflowNode("release", "Release", NodeType.TASK, role="release_manager"),
        WorkflowNode("deploy_staging", "Deploy Staging", NodeType.DEPLOY, role="deployer"),
        WorkflowNode("deploy_production", "Deploy Production", NodeType.DEPLOY, role="deployer"),
        WorkflowNode("done", "Done", NodeType.TERMINAL),
    ]
    edges = [
        WorkflowEdge("e1", "triage", "plan"),
        WorkflowEdge("e2", "plan", "architecture"),
        WorkflowEdge("e3", "architecture", "implementation"),
        WorkflowEdge("e4", "implementation", "validation"),
        WorkflowEdge("e5", "validation", "implementation", condition="validation_failed", loop=True, branch_label="retry"),
        WorkflowEdge("e6", "validation", "review", condition="validation_passed"),
        WorkflowEdge("e7", "review", "implementation", condition="review_blocked", loop=True, branch_label="rework"),
        WorkflowEdge("e8", "review", "security_gate", condition="review_passed"),
        WorkflowEdge("e9", "security_gate", "security_review", condition="sensitive_changes"),
        WorkflowEdge("e10", "security_gate", "approval_gate", condition="non_sensitive"),
        WorkflowEdge("e11", "security_review", "implementation", condition="security_blocked", loop=True, branch_label="fix"),
        WorkflowEdge("e12", "security_review", "approval_gate", condition="security_ok"),
        WorkflowEdge("e13", "approval_gate", "release", condition="approved"),
        WorkflowEdge("e14", "release", "deploy_staging"),
        WorkflowEdge("e15", "deploy_staging", "deploy_production", condition="policy_allows_prod"),
        WorkflowEdge("e16", "deploy_staging", "done", condition="staging_only"),
        WorkflowEdge("e17", "deploy_production", "done"),
    ]
    return WorkflowDefinition(
        workflow_id=f"flow-{flow.value}",
        name=f"{flow.value}-workflow",
        version=version,
        nodes=nodes,
        edges=edges,
        entry_node_id="triage",
        metadata={"flow": flow.value},
    )


def _simple_definition(flow: FlowType, phases: list[str], *, version: str) -> WorkflowDefinition:
    nodes = [WorkflowNode(item, item.replace("_", " ").title(), NodeType.TASK) for item in phases[:-1]]
    nodes.append(WorkflowNode(phases[-1], phases[-1].title(), NodeType.TERMINAL))
    edges: list[WorkflowEdge] = []
    for idx in range(len(phases) - 1):
        edges.append(WorkflowEdge(f"e{idx + 1}", phases[idx], phases[idx + 1]))
    return WorkflowDefinition(
        workflow_id=f"flow-{flow.value}",
        name=f"{flow.value}-workflow",
        version=version,
        nodes=nodes,
        edges=edges,
        entry_node_id=phases[0],
        metadata={"flow": flow.value},
    )
