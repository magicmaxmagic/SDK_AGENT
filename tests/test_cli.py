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
        "feature",
        "Add signup form",
    ])

    assert args.command == "feature"
    assert args.request == "Add signup form"
    assert args.branch_name == "feature/add-signup"
    assert args.allow_commit is True


def test_cli_validate_parsing() -> None:
    parser = _base_parser()
    args = parser.parse_args(["validate"])
    assert args.command == "validate"


def test_cli_dry_run_flag() -> None:
    parser = _base_parser()
    args = parser.parse_args(["--dry-run", "review"])
    assert args.command == "review"
    assert args.dry_run is True
