from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class RuntimeHeartbeat:
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    phase: str = "init"
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "phase": self.phase,
            "message": self.message,
        }


@dataclass(slots=True)
class WorkflowRuntime:
    run_id: str
    heartbeats: list[RuntimeHeartbeat] = field(default_factory=list)

    def heartbeat(self, phase: str, message: str) -> None:
        self.heartbeats.append(RuntimeHeartbeat(phase=phase, message=message))

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "heartbeats": [item.to_dict() for item in self.heartbeats],
        }
