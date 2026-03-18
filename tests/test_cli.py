from sdk_agent.cli import _base_parser


def test_cli_feature_parsing() -> None:
    parser = _base_parser()
    args = parser.parse_args([
        "--repo-path",
        "/tmp/repo",
        "--plugin",
        "nextjs",
        "--branch-name",
        "feature/add-signup",
        "--allow-commit",
        "--allow-staging-deploy",
        "--autonomy-level",
        "implement",
        "feature",
        "Add signup form",
    ])

    assert args.command == "feature"
    assert args.request == "Add signup form"
    assert args.branch_name == "feature/add-signup"
    assert args.allow_commit is True


def test_cli_resume_parsing() -> None:
    parser = _base_parser()
    args = parser.parse_args(["resume", "--run-id", "run-abc"])
    assert args.command == "resume"
    assert args.run_id == "run-abc"


def test_cli_deploy_production_parsing() -> None:
    parser = _base_parser()
    args = parser.parse_args(["deploy-production", "--run-id", "run-1"])
    assert args.command == "deploy-production"


def test_cli_inspect_graph_parsing() -> None:
    parser = _base_parser()
    args = parser.parse_args(["inspect-graph", "--run-id", "run-1"])
    assert args.command == "inspect-graph"
    assert args.run_id == "run-1"


def test_cli_inspect_run_parsing() -> None:
    parser = _base_parser()
    args = parser.parse_args(["inspect-run", "--run-id", "run-2"])
    assert args.command == "inspect-run"
    assert args.run_id == "run-2"


def test_cli_approve_production_parsing() -> None:
    parser = _base_parser()
    args = parser.parse_args(
        [
            "approve-production",
            "--run-id",
            "run-1",
            "--approved-by",
            "oncall.lead",
            "--ticket",
            "CHG-4242",
            "--ticket-source",
            "cab",
            "--reason",
            "CAB approved",
            "--expires-in-minutes",
            "45",
        ]
    )
    assert args.command == "approve-production"
    assert args.approved_by == "oncall.lead"
    assert args.ticket_source == "cab"
    assert args.expires_in_minutes == 45


def test_cli_approve_staging_parsing() -> None:
    parser = _base_parser()
    args = parser.parse_args(
        [
            "approve-staging",
            "--run-id",
            "run-1",
            "--approved-by",
            "release.manager",
            "--ticket",
            "INC-7788",
            "--ticket-source",
            "itsm",
            "--reason",
            "staging gate",
        ]
    )
    assert args.command == "approve-staging"
    assert args.ticket_source == "itsm"


def test_cli_audit_flat_fields_parsing() -> None:
    parser = _base_parser()
    args = parser.parse_args(["audit", "--run-id", "run-1", "--flat-fields"])
    assert args.command == "audit"
    assert args.flat_fields is True


def test_cli_audit_export_siem_parsing() -> None:
    parser = _base_parser()
    args = parser.parse_args(
        [
            "audit-export-siem",
            "--run-id",
            "run-1",
            "--flat-fields",
            "--batch-size",
            "100",
            "--max-file-size-bytes",
            "2048",
        ]
    )
    assert args.command == "audit-export-siem"
    assert args.batch_size == 100
    assert args.max_file_size_bytes == 2048


def test_cli_audit_verify_chain_parsing() -> None:
    parser = _base_parser()
    args = parser.parse_args(["audit-verify-chain", "--run-id", "run-1", "--skip-siem-exports", "--strict"])
    assert args.command == "audit-verify-chain"
    assert args.skip_siem_exports is True
    assert args.strict is True


def test_cli_audit_repair_chain_parsing() -> None:
    parser = _base_parser()
    args = parser.parse_args(["audit-repair-chain", "--run-id", "run-1", "--skip-siem-exports"])
    assert args.command == "audit-repair-chain"
    assert args.skip_siem_exports is True
