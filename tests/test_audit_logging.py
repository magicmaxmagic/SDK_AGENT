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
