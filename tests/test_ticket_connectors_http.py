from __future__ import annotations

import json
from typing import Any

from sdk_agent.core import ticket_connectors as connectors


class _FakeResponse:
    def __init__(self, payload: dict[str, Any], status: int = 200):
        self._payload = payload
        self.status = status

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        return None


def test_jira_http_connector_validates(monkeypatch) -> None:
    def fake_urlopen(request, timeout):  # noqa: ANN001, ARG001
        assert request.full_url.endswith("/rest/api/3/issue/CHG-1234")
        return _FakeResponse({"key": "CHG-1234"})

    monkeypatch.setattr(connectors, "urlopen", fake_urlopen)
    monkeypatch.setenv("JIRA_USER_EMAIL", "bot@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "token")

    connector = connectors.build_ticket_connector(
        "jira",
        {
            "base_url": "https://jira.example.com",
            "auth_mode": "basic",
            "accepted_sources": ["jira"],
        },
    )

    result = connector.validate("CHG-1234", "jira")
    assert result.valid is True
    assert result.provider == "jira"


def test_servicenow_http_connector_validates(monkeypatch) -> None:
    def fake_urlopen(request, timeout):  # noqa: ANN001, ARG001
        assert "change_request" in request.full_url
        return _FakeResponse({"result": [{"number": "INC-9001"}]})

    monkeypatch.setattr(connectors, "urlopen", fake_urlopen)
    monkeypatch.setenv("SERVICENOW_USER", "agent")
    monkeypatch.setenv("SERVICENOW_PASSWORD", "secret")

    connector = connectors.build_ticket_connector(
        "servicenow",
        {
            "base_url": "https://snow.example.com",
            "auth_mode": "basic",
            "accepted_sources": ["itsm"],
        },
    )

    result = connector.validate("INC-9001", "itsm")
    assert result.valid is True
    assert result.provider == "servicenow"


def test_jira_http_connector_reports_missing_ticket(monkeypatch) -> None:
    def fake_urlopen(request, timeout):  # noqa: ANN001, ARG001
        return _FakeResponse({"errorMessages": ["Issue does not exist"]})

    monkeypatch.setattr(connectors, "urlopen", fake_urlopen)

    connector = connectors.build_ticket_connector(
        "jira",
        {
            "base_url": "https://jira.example.com",
            "auth_mode": "bearer",
            "accepted_sources": ["jira"],
        },
    )

    result = connector.validate("CHG-7777", "jira")
    assert result.valid is False
    assert "not found" in result.reason
