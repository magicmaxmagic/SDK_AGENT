import json
from pathlib import Path

from sdk_agent.core.audit import AuditLogger


def test_audit_logging_roundtrip(tmp_path: Path) -> None:
    logger = AuditLogger(run_dir=tmp_path / "run-1")
    logger.record("phase", {"value": "plan"})
    logger.record("decision", {"allowed": True})

    entries = logger.read_all()
    assert len(entries) == 2
    assert entries[0]["event"] == "phase"
    assert entries[0]["schema_version"] == "siem.audit.v1"
    assert entries[0]["event_version"] == 1
    assert entries[0]["run_id"] == "run-1"
    assert "siem" in entries[0]
    assert entries[0]["siem"]["service.name"] == "sdk_agent"
    assert "forensics" in entries[0]
    assert entries[0]["forensics"]["algorithm"] == "sha256"
    assert entries[0]["forensics"]["chain_hash"]
    assert entries[1]["forensics"]["prev_hash"] == entries[0]["forensics"]["chain_hash"]


def test_audit_logging_flat_export(tmp_path: Path) -> None:
    logger = AuditLogger(run_dir=tmp_path / "run-2")
    logger.record("deploy_staging_succeeded", {"run_id": "run-2", "exit_code": 0}, status="success", role="deployer")

    entries = logger.read_flat()
    assert len(entries) == 1
    assert entries[0]["sdk_agent.run_id"] == "run-2"
    assert entries[0]["event.category"] == "deployment"
    assert entries[0]["event.type"] == "change"
    assert entries[0]["event.outcome"] == "success"


def test_audit_ndjson_export_rotates_files(tmp_path: Path) -> None:
    logger = AuditLogger(run_dir=tmp_path / "run-3")
    for idx in range(10):
        logger.record("deploy_staging_succeeded", {"run_id": "run-3", "index": idx}, status="success", role="deployer")

    files = logger.export_siem_ndjson(flat_fields=True, batch_size=10, max_file_size_bytes=300)
    assert len(files) >= 2
    for file in files:
        assert file.exists()
        assert file.suffix == ".ndjson"

    manifest = (tmp_path / "run-3" / "siem_exports" / "siem_export_manifest.json")
    assert manifest.exists()


def test_ticket_validation_log_is_chain_signed(tmp_path: Path) -> None:
    logger = AuditLogger(run_dir=tmp_path / "run-4")
    logger.record_ticket_validation({"run_id": "run-4", "ticket_id": "CHG-1001", "status": "approved"})
    logger.record_ticket_validation({"run_id": "run-4", "ticket_id": "CHG-1002", "status": "rejected"})

    lines = logger.ticket_validation_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2

    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["forensics"]["chain_hash"]
    assert second["forensics"]["prev_hash"] == first["forensics"]["chain_hash"]


def test_verify_chain_success(tmp_path: Path) -> None:
    logger = AuditLogger(run_dir=tmp_path / "run-5")
    logger.record("phase", {"run_id": "run-5", "value": "plan"})
    logger.record_ticket_validation({"run_id": "run-5", "ticket_id": "CHG-1001", "status": "approved"})
    logger.export_siem_ndjson(flat_fields=True, batch_size=10, max_file_size_bytes=1024)

    report = logger.verify_chain(include_siem_exports=True)
    assert report["valid"] is True
    assert report["audit_log"]["valid"] is True
    assert report["ticket_validation_log"]["valid"] is True


def test_verify_chain_detects_tampering(tmp_path: Path) -> None:
    logger = AuditLogger(run_dir=tmp_path / "run-6")
    logger.record("phase", {"run_id": "run-6", "value": "plan"})
    logger.record("phase", {"run_id": "run-6", "value": "validate"})

    lines = logger.audit_file.read_text(encoding="utf-8").splitlines()
    payload = json.loads(lines[1])
    payload["data"]["value"] = "tampered"
    lines[1] = json.dumps(payload, ensure_ascii=True)
    logger.audit_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    report = logger.verify_chain(include_siem_exports=False)
    assert report["valid"] is False
    assert report["audit_log"]["valid"] is False


def test_verify_chain_strict_fails_without_siem_manifest(tmp_path: Path) -> None:
    logger = AuditLogger(run_dir=tmp_path / "run-7")
    logger.record("phase", {"run_id": "run-7", "value": "plan"})

    report = logger.verify_chain(include_siem_exports=True, strict=True)
    assert report["valid"] is False
    assert report["siem_exports"]["valid"] is False


def test_repair_chain_rebuilds_tampered_snapshot(tmp_path: Path) -> None:
    logger = AuditLogger(run_dir=tmp_path / "run-8")
    logger.record("phase", {"run_id": "run-8", "value": "plan"})
    logger.record("phase", {"run_id": "run-8", "value": "validate"})

    lines = logger.audit_file.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[1])
    tampered["forensics"]["chain_hash"] = "deadbeef"
    lines[1] = json.dumps(tampered, ensure_ascii=True)
    logger.audit_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    verify = logger.verify_chain(include_siem_exports=False)
    assert verify["valid"] is False

    repair = logger.repair_chain(include_siem_exports=False)
    assert repair["ok"] is True
    assert repair["messages"]
    repaired_file = Path(repair["files"]["audit_log.jsonl"]["output"])
    repaired_logger = AuditLogger(run_dir=repaired_file.parent)
    repaired_verify = repaired_logger.verify_chain(include_siem_exports=False)
    assert repaired_verify["valid"] is True
