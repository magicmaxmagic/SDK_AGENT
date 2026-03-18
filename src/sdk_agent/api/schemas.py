from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class GraphPayload:
    graph: dict[str, Any]


@dataclass(slots=True)
class RunPayload:
    run: dict[str, Any]


@dataclass(slots=True)
class AuditPayload:
    events: list[dict[str, Any]]
