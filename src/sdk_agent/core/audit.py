from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "siem.audit.v1"
EVENT_VERSION = 1


@dataclass(slots=True)
class AuditLogger:
    run_dir: Path

    @property
    def audit_file(self) -> Path:
        return self.run_dir / "audit_log.jsonl"

    def record(
        self,
        event: str,
        data: dict[str, Any],
        *,
        status: str = "info",
        role: str | None = None,
        action: str | None = None,
    ) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        run_id = str(data.get("run_id", "")) or self.run_dir.name
        mapping = _siem_mapping(event)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "event_version": EVENT_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "event_type": event,
            "run_id": run_id,
            "correlation_id": run_id,
            "status": status,
            "actor_role": role,
            "action": action,
            "data": data,
            "siem": {
                "event.category": mapping["category"],
                "event.type": mapping["type"],
                "event.outcome": mapping["outcome"] if status == "info" else status,
                "service.name": "sdk_agent",
                "labels.schema_version": SCHEMA_VERSION,
            },
        }
        with self.audit_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        if not self.audit_file.exists():
            return []
        return [json.loads(line) for line in self.audit_file.read_text(encoding="utf-8").splitlines() if line.strip()]


def _siem_mapping(event: str) -> dict[str, str]:
    if event.startswith("policy_"):
        return {"category": "policy", "type": "access", "outcome": "unknown"}
    if event.startswith("deploy_"):
        return {"category": "deployment", "type": "change", "outcome": "unknown"}
    if event.startswith("rollback_"):
        return {"category": "deployment", "type": "rollback", "outcome": "unknown"}
    if event.startswith("workflow_"):
        return {"category": "process", "type": "state", "outcome": "unknown"}
    return {"category": "application", "type": "info", "outcome": "unknown"}
