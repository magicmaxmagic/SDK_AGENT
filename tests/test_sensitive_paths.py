from sdk_agent.core.sensitivity import classify_sensitive_changes


def test_sensitive_path_detection() -> None:
    report = classify_sensitive_changes([
        "src/auth/login.py",
        "infra/terraform/main.tf",
        "app/views/home.py",
    ])

    assert report.requires_security_review is True
    assert "src/auth/login.py" in report.sensitive_files
    assert "infrastructure" in report.categories
