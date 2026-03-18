from __future__ import annotations

from typing import Any

from sdk_agent.graph.layout import compute_layout
from sdk_agent.graph.models import WorkflowDefinition, WorkflowRun


def serialize_definition(definition: WorkflowDefinition) -> dict[str, Any]:
    payload = definition.to_dict()
    payload["layout"] = compute_layout(definition)
    return payload


def serialize_run(run: WorkflowRun) -> dict[str, Any]:
    payload = run.to_dict()
    payload["layout"] = compute_layout(run.definition)
    return payload
