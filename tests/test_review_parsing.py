from sdk_agent.roles.reviewer import parse_review_findings


def test_parse_review_findings_structured() -> None:
    text = "Null check missing | high | src/app.py | true | Add guard before dereference"
    findings = parse_review_findings(text)

    assert len(findings) == 1
    assert findings[0].title == "Null check missing"
    assert findings[0].blocking is True
    assert findings[0].file_path == "src/app.py"
    assert findings[0].recommendation.startswith("Add guard")


def test_parse_review_findings_fallback() -> None:
    findings = parse_review_findings("General concerns about missing tests")
    assert len(findings) == 1
    assert findings[0].title == "Review summary"
