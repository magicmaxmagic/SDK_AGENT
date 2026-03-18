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
            "--reason",
            "CAB approved",
            "--expires-in-minutes",
            "45",
        ]
    )
    assert args.command == "approve-production"
    assert args.approved_by == "oncall.lead"
    assert args.expires_in_minutes == 45


def test_cli_audit_flat_fields_parsing() -> None:
    parser = _base_parser()
    args = parser.parse_args(["audit", "--run-id", "run-1", "--flat-fields"])
    assert args.command == "audit"
    assert args.flat_fields is True
