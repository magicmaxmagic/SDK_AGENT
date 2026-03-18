from pathlib import Path

from sdk_agent.core.audit import AuditLogger


def test_audit_logging_roundtrip(tmp_path: Path) -> None:
    logger = AuditLogger(run_dir=tmp_path / "run-1")
    logger.record("phase", {"value": "plan"})
    logger.record("decision", {"allowed": True})

    entries = logger.read_all()
    assert len(entries) == 2
    assert entries[0]["event"] == "phase"
