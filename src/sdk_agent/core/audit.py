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

    def read_flat(self) -> list[dict[str, Any]]:
        return [_flatten_event(entry) for entry in self.read_all()]

    def export_siem_ndjson(
        self,
        *,
        flat_fields: bool = True,
        batch_size: int = 500,
        max_file_size_bytes: int = 1_000_000,
    ) -> list[Path]:
        if batch_size <= 0:
            raise ValueError("batch_size must be > 0")
        if max_file_size_bytes <= 0:
            raise ValueError("max_file_size_bytes must be > 0")

        entries = self.read_flat() if flat_fields else self.read_all()
        export_dir = self.run_dir / "siem_exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        exported: list[Path] = []
        chunk: list[dict[str, Any]] = []
        for entry in entries:
            chunk.append(entry)
            if len(chunk) >= batch_size:
                exported.extend(_write_rotated_chunk(export_dir, chunk, max_file_size_bytes))
                chunk = []
        if chunk:
            exported.extend(_write_rotated_chunk(export_dir, chunk, max_file_size_bytes))
        return exported


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


def _flatten_event(entry: dict[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = {
        "@timestamp": entry.get("timestamp"),
        "event.action": entry.get("action") or entry.get("event_type"),
        "event.category": _nested_get(entry, "siem", "event.category"),
        "event.type": _nested_get(entry, "siem", "event.type"),
        "event.outcome": _nested_get(entry, "siem", "event.outcome"),
        "event.kind": "event",
        "service.name": _nested_get(entry, "siem", "service.name") or "sdk_agent",
        "labels.schema_version": _nested_get(entry, "siem", "labels.schema_version"),
        "sdk_agent.event_type": entry.get("event_type"),
        "sdk_agent.status": entry.get("status"),
        "sdk_agent.run_id": entry.get("run_id"),
        "sdk_agent.correlation_id": entry.get("correlation_id"),
        "user.name": entry.get("actor_role"),
        "message": entry.get("event"),
    }

    data = entry.get("data")
    if isinstance(data, dict):
        for key, value in data.items():
            flat[f"sdk_agent.data.{key}"] = value

    return flat


def _nested_get(payload: dict[str, Any], section: str, key: str) -> Any:
    value = payload.get(section)
    if not isinstance(value, dict):
        return None
    return value.get(key)


def _write_rotated_chunk(export_dir: Path, entries: list[dict[str, Any]], max_file_size_bytes: int) -> list[Path]:
    files: list[Path] = []
    index = _next_export_index(export_dir)
    current_path = export_dir / f"siem_export_{index:04d}.ndjson"
    current_size = 0
    created_current = False

    for entry in entries:
        line = json.dumps(entry, ensure_ascii=True) + "\n"
        line_size = len(line.encode("utf-8"))
        if current_size > 0 and current_size + line_size > max_file_size_bytes:
            if created_current:
                files.append(current_path)
            index += 1
            current_path = export_dir / f"siem_export_{index:04d}.ndjson"
            current_size = 0
            created_current = False

        with current_path.open("a", encoding="utf-8") as handle:
            handle.write(line)
        current_size += line_size
        created_current = True

    if created_current:
        files.append(current_path)
    return files


def _next_export_index(export_dir: Path) -> int:
    existing = sorted(export_dir.glob("siem_export_*.ndjson"))
    if not existing:
        return 1
    latest = existing[-1].stem
    suffix = latest.rsplit("_", maxsplit=1)[-1]
    try:
        return int(suffix) + 1
    except ValueError:
        return len(existing) + 1
