from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    TASK = "task"
    GATE = "gate"
    APPROVAL = "approval"
    DEPLOY = "deploy"
    TERMINAL = "terminal"


class NodeStatus(str, Enum):
    WAITING = "waiting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


@dataclass(slots=True)
class WorkflowNode:
    node_id: str
    label: str
    node_type: NodeType
    role: str | None = None
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["node_type"] = self.node_type.value
        return payload


@dataclass(slots=True)
class WorkflowEdge:
    edge_id: str
    source: str
    target: str
    condition: str | None = None
    branch_label: str | None = None
    loop: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class WorkflowDefinition:
    workflow_id: str
    name: str
    version: str
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]
    entry_node_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "version": self.version,
            "entry_node_id": self.entry_node_id,
            "metadata": dict(self.metadata),
            "nodes": [item.to_dict() for item in self.nodes],
            "edges": [item.to_dict() for item in self.edges],
        }


@dataclass(slots=True)
class RetryRecord:
    node_id: str
    retry_index: int
    reason: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["timestamp"] = self.timestamp.isoformat()
        return payload


@dataclass(slots=True)
class BranchDecision:
    node_id: str
    chosen_edge_id: str
    reason: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["timestamp"] = self.timestamp.isoformat()
        return payload


@dataclass(slots=True)
class PolicyDecisionRecord:
    node_id: str
    action: str
    allowed: bool
    reason: str
    role: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["timestamp"] = self.timestamp.isoformat()
        return payload


@dataclass(slots=True)
class ApprovalGate:
    node_id: str
    target: str
    required_approvals: int
    active_approvals: int
    approved: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class NodeExecutionState:
    node_id: str
    status: NodeStatus
    input_payload: dict[str, Any] = field(default_factory=dict)
    output_payload: dict[str, Any] = field(default_factory=dict)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    retries: list[RetryRecord] = field(default_factory=list)
    branch_decisions: list[BranchDecision] = field(default_factory=list)
    policy_decisions: list[PolicyDecisionRecord] = field(default_factory=list)
    failure_reason: str | None = None
    artifacts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "status": self.status.value,
            "input_payload": dict(self.input_payload),
            "output_payload": dict(self.output_payload),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "retries": [item.to_dict() for item in self.retries],
            "branch_decisions": [item.to_dict() for item in self.branch_decisions],
            "policy_decisions": [item.to_dict() for item in self.policy_decisions],
            "failure_reason": self.failure_reason,
            "artifacts": list(self.artifacts),
        }


@dataclass(slots=True)
class WorkflowRun:
    run_id: str
    definition: WorkflowDefinition
    current_node_id: str | None
    node_states: list[NodeExecutionState] = field(default_factory=list)
    status: str = "running"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "definition": self.definition.to_dict(),
            "current_node_id": self.current_node_id,
            "status": self.status,
            "metadata": dict(self.metadata),
            "node_states": [item.to_dict() for item in self.node_states],
        }
