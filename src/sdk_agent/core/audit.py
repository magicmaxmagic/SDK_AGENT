from __future__ import annotations

import hashlib
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

    @property
    def ticket_validation_file(self) -> Path:
        return self.run_dir / "ticket_validation_log.jsonl"

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
        _append_signed_json_line(self.audit_file, payload)

    def record_ticket_validation(self, data: dict[str, Any]) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "event_version": EVENT_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "ticket_validation",
            "event_type": "ticket_validation",
            "run_id": str(data.get("run_id", "")) or self.run_dir.name,
            "data": data,
        }
        _append_signed_json_line(self.ticket_validation_file, payload)

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
        export_chain_hash: str | None = None
        chunk: list[dict[str, Any]] = []
        for entry in entries:
            chunk.append(entry)
            if len(chunk) >= batch_size:
                files, export_chain_hash = _write_rotated_chunk(
                    export_dir,
                    chunk,
                    max_file_size_bytes,
                    prev_hash=export_chain_hash,
                )
                exported.extend(files)
                chunk = []
        if chunk:
            files, export_chain_hash = _write_rotated_chunk(
                export_dir,
                chunk,
                max_file_size_bytes,
                prev_hash=export_chain_hash,
            )
            exported.extend(files)

        manifest = {
            "schema_version": SCHEMA_VERSION,
            "event_version": EVENT_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "algorithm": "sha256",
            "entry_count": len(entries),
            "file_count": len(exported),
            "final_chain_hash": export_chain_hash,
            "files": [str(path.name) for path in exported],
        }
        (export_dir / "siem_export_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
        return exported

    def verify_chain(self, *, include_siem_exports: bool = True, strict: bool = False) -> dict[str, Any]:
        audit_report = _verify_signed_jsonl_file(self.audit_file)
        ticket_report = _verify_signed_jsonl_file(self.ticket_validation_file)

        siem_report: dict[str, Any] = {"valid": True, "checked": False, "reason": "siem verification skipped"}
        if include_siem_exports:
            siem_report = self._verify_siem_exports(strict=strict)

        overall_valid = bool(audit_report.get("valid", False)) and bool(ticket_report.get("valid", False)) and bool(siem_report.get("valid", False))
        return {
            "valid": overall_valid,
            "audit_log": audit_report,
            "ticket_validation_log": ticket_report,
            "siem_exports": siem_report,
        }

    def repair_chain(self, *, include_siem_exports: bool = True) -> dict[str, Any]:
        """Rebuild signed chain into an immutable repair snapshot directory.

        This function never mutates original artifacts and always returns a detailed report.
        """

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        repair_root = self.run_dir / "forensics_repair" / timestamp
        repair_root.mkdir(parents=True, exist_ok=True)
        report: dict[str, Any] = {
            "ok": True,
            "run_dir": str(self.run_dir),
            "repair_dir": str(repair_root),
            "messages": [],
            "files": {},
        }

        audit_dst = repair_root / self.audit_file.name
        report["files"][self.audit_file.name] = _repair_single_jsonl(self.audit_file, audit_dst)
        report["messages"].append(f"processed {self.audit_file.name}")

        ticket_dst = repair_root / self.ticket_validation_file.name
        report["files"][self.ticket_validation_file.name] = _repair_single_jsonl(self.ticket_validation_file, ticket_dst)
        report["messages"].append(f"processed {self.ticket_validation_file.name}")

        if include_siem_exports:
            siem_src_dir = self.run_dir / "siem_exports"
            siem_dst_dir = repair_root / "siem_exports"
            siem_dst_dir.mkdir(parents=True, exist_ok=True)
            siem_result = self._repair_siem_exports(source_dir=siem_src_dir, destination_dir=siem_dst_dir)
            report["files"]["siem_exports"] = siem_result
            report["messages"].append("processed siem exports")

        report["ok"] = all(bool(item.get("ok", False)) for item in report["files"].values())
        if not report["messages"]:
            report["messages"] = ["no files were processed"]
            report["ok"] = False
        return report

    def _verify_siem_exports(self, *, strict: bool) -> dict[str, Any]:
        export_dir = self.run_dir / "siem_exports"
        if not export_dir.exists():
            if strict:
                return {"valid": False, "checked": True, "reason": "siem export directory missing in strict mode"}
            return {"valid": True, "checked": True, "reason": "no siem exports"}

        manifest_path = export_dir / "siem_export_manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {"valid": False, "checked": True, "reason": "invalid siem manifest JSON"}

            files = []
            for item in manifest.get("files", []):
                if isinstance(item, str) and item.strip():
                    files.append(export_dir / item)
            if strict and not files:
                return {"valid": False, "checked": True, "reason": "siem manifest has no files in strict mode"}
            report = _verify_signed_jsonl_paths(files)
            report["checked"] = True
            if report.get("valid", False):
                expected = manifest.get("final_chain_hash")
                if expected != report.get("final_hash"):
                    report["valid"] = False
                    report["reason"] = "manifest final_chain_hash mismatch"
                if strict:
                    existing = sorted(export_dir.glob("siem_export_*.ndjson"))
                    expected_paths = {path.name for path in files}
                    existing_paths = {path.name for path in existing}
                    if expected_paths != existing_paths:
                        report["valid"] = False
                        report["reason"] = "manifest file list incomplete in strict mode"
            return report

        if strict:
            return {"valid": False, "checked": True, "reason": "siem manifest missing in strict mode"}

        files = sorted(export_dir.glob("siem_export_*.ndjson"))
        report = _verify_signed_jsonl_paths(files)
        report["checked"] = True
        return report

    def _repair_siem_exports(self, *, source_dir: Path, destination_dir: Path) -> dict[str, Any]:
        files = sorted(source_dir.glob("siem_export_*.ndjson")) if source_dir.exists() else []
        if not files:
            return {"ok": True, "reason": "no siem export files", "files": []}

        outputs: list[str] = []
        previous_hash: str | None = None
        total_entries = 0
        for source in files:
            destination = destination_dir / source.name
            repair = _repair_single_jsonl(source, destination, previous_hash=previous_hash)
            outputs.append(source.name)
            total_entries += int(repair.get("entries", 0))
            previous_hash = repair.get("final_hash")
            if not repair.get("ok", False):
                return {
                    "ok": False,
                    "reason": f"failed to repair {source.name}: {repair.get('reason', 'unknown')}",
                    "files": outputs,
                    "entries": total_entries,
                }

        manifest = {
            "schema_version": SCHEMA_VERSION,
            "event_version": EVENT_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "algorithm": "sha256",
            "entry_count": total_entries,
            "file_count": len(outputs),
            "final_chain_hash": previous_hash,
            "files": outputs,
            "repaired_from": str(source_dir),
        }
        (destination_dir / "siem_export_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
        return {"ok": True, "files": outputs, "entries": total_entries, "final_hash": previous_hash}


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


def _write_rotated_chunk(
    export_dir: Path,
    entries: list[dict[str, Any]],
    max_file_size_bytes: int,
    *,
    prev_hash: str | None,
) -> tuple[list[Path], str | None]:
    files: list[Path] = []
    index = _next_export_index(export_dir)
    current_path = export_dir / f"siem_export_{index:04d}.ndjson"
    current_size = 0
    created_current = False
    running_hash = prev_hash

    for entry in entries:
        signed_entry = _with_chain_signature(entry, previous_hash=running_hash)
        running_hash = _extract_chain_hash(signed_entry)
        line = json.dumps(signed_entry, ensure_ascii=True) + "\n"
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
    return files, running_hash


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


def _append_signed_json_line(path: Path, payload: dict[str, Any]) -> str:
    prev_hash = _last_chain_hash(path)
    signed = _with_chain_signature(payload, previous_hash=prev_hash)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(signed, ensure_ascii=True) + "\n")
    return _extract_chain_hash(signed)


def _with_chain_signature(payload: dict[str, Any], *, previous_hash: str | None) -> dict[str, Any]:
    materialized = dict(payload)
    canonical = json.dumps(materialized, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    chain_input = f"{previous_hash or ''}:{canonical}".encode("utf-8")
    chain_hash = hashlib.sha256(chain_input).hexdigest()
    materialized["forensics"] = {
        "algorithm": "sha256",
        "prev_hash": previous_hash,
        "chain_hash": chain_hash,
    }
    return materialized


def _extract_chain_hash(payload: dict[str, Any]) -> str | None:
    value = payload.get("forensics")
    if not isinstance(value, dict):
        return None
    chain_hash = value.get("chain_hash")
    if isinstance(chain_hash, str) and chain_hash.strip():
        return chain_hash
    return None


def _last_chain_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return None
    try:
        payload = json.loads(lines[-1])
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return _extract_chain_hash(payload)


def _verify_signed_jsonl_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"valid": True, "entries": 0, "final_hash": None, "reason": "file missing"}
    return _verify_signed_jsonl_paths([path])


def _verify_signed_jsonl_paths(paths: list[Path]) -> dict[str, Any]:
    previous_hash: str | None = None
    entries = 0
    for path in paths:
        if not path.exists():
            return {"valid": False, "entries": entries, "final_hash": previous_hash, "reason": f"missing file: {path.name}"}
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            entries += 1
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                return {
                    "valid": False,
                    "entries": entries,
                    "final_hash": previous_hash,
                    "reason": f"invalid JSON at {path.name}:{line_no}",
                }
            if not isinstance(payload, dict):
                return {
                    "valid": False,
                    "entries": entries,
                    "final_hash": previous_hash,
                    "reason": f"invalid payload type at {path.name}:{line_no}",
                }
            forensics = payload.get("forensics")
            if not isinstance(forensics, dict):
                return {
                    "valid": False,
                    "entries": entries,
                    "final_hash": previous_hash,
                    "reason": f"missing forensics at {path.name}:{line_no}",
                }
            if forensics.get("prev_hash") != previous_hash:
                return {
                    "valid": False,
                    "entries": entries,
                    "final_hash": previous_hash,
                    "reason": f"prev_hash mismatch at {path.name}:{line_no}",
                }

            unsigned_payload = dict(payload)
            unsigned_payload.pop("forensics", None)
            expected = _with_chain_signature(unsigned_payload, previous_hash=previous_hash).get("forensics", {}).get("chain_hash")
            current = forensics.get("chain_hash")
            if expected != current:
                return {
                    "valid": False,
                    "entries": entries,
                    "final_hash": previous_hash,
                    "reason": f"chain_hash mismatch at {path.name}:{line_no}",
                }
            previous_hash = current if isinstance(current, str) else previous_hash

    return {"valid": True, "entries": entries, "final_hash": previous_hash}


def _repair_single_jsonl(source: Path, destination: Path, *, previous_hash: str | None = None) -> dict[str, Any]:
    if not source.exists():
        return {"ok": True, "entries": 0, "final_hash": previous_hash, "reason": "source missing"}

    destination.parent.mkdir(parents=True, exist_ok=True)
    repaired_lines: list[str] = []
    entries = 0
    running_hash = previous_hash

    for line_no, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return {
                "ok": False,
                "entries": entries,
                "final_hash": running_hash,
                "reason": f"invalid JSON at line {line_no}",
            }
        if not isinstance(payload, dict):
            return {
                "ok": False,
                "entries": entries,
                "final_hash": running_hash,
                "reason": f"invalid payload type at line {line_no}",
            }

        unsigned_payload = dict(payload)
        unsigned_payload.pop("forensics", None)
        signed = _with_chain_signature(unsigned_payload, previous_hash=running_hash)
        running_hash = _extract_chain_hash(signed)
        repaired_lines.append(json.dumps(signed, ensure_ascii=True))
        entries += 1

    destination.write_text(("\n".join(repaired_lines) + "\n") if repaired_lines else "", encoding="utf-8")
    return {"ok": True, "entries": entries, "final_hash": running_hash, "output": str(destination)}
