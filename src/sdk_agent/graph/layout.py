from __future__ import annotations

from typing import Any

from sdk_agent.graph.models import WorkflowDefinition


LEVEL_SPACING = 220
ROW_SPACING = 130


def compute_layout(definition: WorkflowDefinition) -> dict[str, Any]:
    """Compute deterministic grid layout metadata for future UI renderers."""

    order = _ordered_nodes(definition)
    positions: dict[str, dict[str, int]] = {}
    for index, node_id in enumerate(order):
        positions[node_id] = {
            "x": (index % 5) * LEVEL_SPACING,
            "y": (index // 5) * ROW_SPACING,
        }

    return {
        "engine": "grid-v1",
        "positions": positions,
        "entry_node_id": definition.entry_node_id,
    }


def _ordered_nodes(definition: WorkflowDefinition) -> list[str]:
    ids = [item.node_id for item in definition.nodes]
    if definition.entry_node_id in ids:
        ids.remove(definition.entry_node_id)
        return [definition.entry_node_id] + ids
    return ids
