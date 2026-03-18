from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


@dataclass(slots=True)
class TicketValidationResult:
    valid: bool
    reason: str
    normalized_ticket_id: str | None = None
    provider: str | None = None
    metadata: dict[str, Any] | None = None


class ChangeTicketConnector(Protocol):
    name: str

    def validate(self, ticket_id: str, ticket_source: str) -> TicketValidationResult:
        ...


@dataclass(slots=True)
class MockTicketConnector:
    settings: dict[str, Any]
    name: str = "mock"

    def validate(self, ticket_id: str, ticket_source: str) -> TicketValidationResult:
        normalized_id = ticket_id.strip().upper()
        source = ticket_source.strip().lower()
        allowed_sources = {
            item.strip().lower() for item in self.settings.get("allowed_sources", ["cab", "itsm", "jira"]) if str(item).strip()
        }
        if source not in allowed_sources:
            return TicketValidationResult(False, f"ticket source '{source}' is not supported by mock connector", provider=self.name)

        pattern = str(self.settings.get("ticket_pattern", r"^(CHG|RFC|INC)-[0-9]{3,}$"))
        if not re.fullmatch(pattern, normalized_id):
            return TicketValidationResult(False, f"ticket '{normalized_id}' rejected by mock connector pattern", provider=self.name)

        known = self._known_tickets()
        strict_known = bool(self.settings.get("strict_known", False))
        if strict_known:
            source_known = known.get(source, set())
            if normalized_id not in source_known:
                return TicketValidationResult(False, f"ticket '{normalized_id}' not found in mock registry for source '{source}'", provider=self.name)

        return TicketValidationResult(
            True,
            "validated by mock connector",
            normalized_ticket_id=normalized_id,
            provider=self.name,
            metadata={"source": source},
        )

    def _known_tickets(self) -> dict[str, set[str]]:
        payload = self.settings.get("known_tickets", {})
        if not isinstance(payload, dict):
            return {}
        result: dict[str, set[str]] = {}
        for source, values in payload.items():
            if isinstance(values, list):
                result[str(source).strip().lower()] = {str(item).strip().upper() for item in values if str(item).strip()}
        return result


@dataclass(slots=True)
class JiraTicketConnector:
    settings: dict[str, Any]
    name: str = "jira"

    def validate(self, ticket_id: str, ticket_source: str) -> TicketValidationResult:
        normalized_id = ticket_id.strip().upper()
        source = ticket_source.strip().lower()
        accepted_sources = {item.strip().lower() for item in self.settings.get("accepted_sources", ["jira"]) if str(item).strip()}
        if source not in accepted_sources:
            return TicketValidationResult(False, f"source '{source}' is not routed to jira connector", provider=self.name)

        json_file = self.settings.get("mock_file")
        if json_file:
            registry = _load_mock_registry(Path(str(json_file)))
            if normalized_id in registry:
                return TicketValidationResult(True, "validated by jira connector mock file", normalized_ticket_id=normalized_id, provider=self.name)
            return TicketValidationResult(False, f"ticket '{normalized_id}' not found in jira mock file", provider=self.name)

        base_url = str(self.settings.get("base_url", "")).strip()
        if not base_url:
            return TicketValidationResult(False, "jira connector requires external client configuration", provider=self.name)

        path_template = str(self.settings.get("issue_path", "/rest/api/3/issue/{ticket_id}"))
        issue_url = f"{base_url.rstrip('/')}{path_template.format(ticket_id=quote(normalized_id, safe=''))}"
        headers = _build_auth_headers(
            settings=self.settings,
            token_env_default="JIRA_API_TOKEN",
            user_env_default="JIRA_USER_EMAIL",
            password_env_default="JIRA_API_TOKEN",
            default_auth_mode="basic",
        )
        payload, error = _http_get_json(issue_url, headers=headers, timeout_seconds=_timeout(self.settings))
        if error is not None:
            return TicketValidationResult(False, f"jira connector request failed: {error}", provider=self.name)

        if isinstance(payload, dict) and payload.get("key"):
            return TicketValidationResult(
                True,
                "validated by jira connector HTTP API",
                normalized_ticket_id=normalized_id,
                provider=self.name,
                metadata={"url": issue_url, "key": payload.get("key")},
            )

        return TicketValidationResult(False, f"ticket '{normalized_id}' not found in jira response", provider=self.name)


@dataclass(slots=True)
class ServiceNowTicketConnector:
    settings: dict[str, Any]
    name: str = "servicenow"

    def validate(self, ticket_id: str, ticket_source: str) -> TicketValidationResult:
        normalized_id = ticket_id.strip().upper()
        source = ticket_source.strip().lower()
        accepted_sources = {item.strip().lower() for item in self.settings.get("accepted_sources", ["itsm", "cab"]) if str(item).strip()}
        if source not in accepted_sources:
            return TicketValidationResult(False, f"source '{source}' is not routed to servicenow connector", provider=self.name)

        json_file = self.settings.get("mock_file")
        if json_file:
            registry = _load_mock_registry(Path(str(json_file)))
            if normalized_id in registry:
                return TicketValidationResult(True, "validated by servicenow connector mock file", normalized_ticket_id=normalized_id, provider=self.name)
            return TicketValidationResult(False, f"ticket '{normalized_id}' not found in servicenow mock file", provider=self.name)

        base_url = str(self.settings.get("base_url", "")).strip()
        if not base_url:
            return TicketValidationResult(False, "servicenow connector requires external client configuration", provider=self.name)

        path_template = str(
            self.settings.get(
                "issue_path",
                "/api/now/table/change_request?sysparm_query=number={ticket_id}&sysparm_limit=1",
            )
        )
        issue_url = f"{base_url.rstrip('/')}{path_template.format(ticket_id=quote(normalized_id, safe=''))}"
        headers = _build_auth_headers(
            settings=self.settings,
            token_env_default="SERVICENOW_API_TOKEN",
            user_env_default="SERVICENOW_USER",
            password_env_default="SERVICENOW_PASSWORD",
            default_auth_mode="basic",
        )
        payload, error = _http_get_json(issue_url, headers=headers, timeout_seconds=_timeout(self.settings))
        if error is not None:
            return TicketValidationResult(False, f"servicenow connector request failed: {error}", provider=self.name)

        if isinstance(payload, dict):
            result = payload.get("result")
            if isinstance(result, list) and result:
                return TicketValidationResult(
                    True,
                    "validated by servicenow connector HTTP API",
                    normalized_ticket_id=normalized_id,
                    provider=self.name,
                    metadata={"url": issue_url, "match_count": len(result)},
                )
            if isinstance(result, dict) and result:
                return TicketValidationResult(
                    True,
                    "validated by servicenow connector HTTP API",
                    normalized_ticket_id=normalized_id,
                    provider=self.name,
                    metadata={"url": issue_url, "match_count": 1},
                )

        return TicketValidationResult(False, f"ticket '{normalized_id}' not found in servicenow response", provider=self.name)


@dataclass(slots=True)
class CompositeTicketConnector:
    routing: dict[str, ChangeTicketConnector]
    fallback: ChangeTicketConnector
    name: str = "composite"

    def validate(self, ticket_id: str, ticket_source: str) -> TicketValidationResult:
        source = ticket_source.strip().lower()
        connector = self.routing.get(source, self.fallback)
        return connector.validate(ticket_id=ticket_id, ticket_source=ticket_source)


def build_ticket_connector(kind: str, settings: dict[str, Any]) -> ChangeTicketConnector:
    connector_kind = (kind or "mock").strip().lower()
    payload = dict(settings or {})

    if connector_kind == "mock":
        return MockTicketConnector(settings=payload)

    if connector_kind == "jira":
        return JiraTicketConnector(settings=payload)

    if connector_kind == "servicenow":
        return ServiceNowTicketConnector(settings=payload)

    if connector_kind == "composite":
        jira = JiraTicketConnector(settings=payload)
        servicenow = ServiceNowTicketConnector(settings=payload)
        fallback = MockTicketConnector(settings=payload)
        return CompositeTicketConnector(
            routing={"jira": jira, "itsm": servicenow, "cab": servicenow},
            fallback=fallback,
        )

    raise ValueError(f"Unsupported ticket connector kind: {connector_kind}")


def _load_mock_registry(path: Path) -> set[str]:
    if not path.exists():
        return set()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return {str(item).strip().upper() for item in payload if str(item).strip()}
    if isinstance(payload, dict):
        values = payload.get("tickets", [])
        if isinstance(values, list):
            return {str(item).strip().upper() for item in values if str(item).strip()}
    return set()


def _timeout(settings: dict[str, Any]) -> float:
    raw = settings.get("timeout_seconds", 10)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 10.0
    return max(1.0, value)


def _build_auth_headers(
    *,
    settings: dict[str, Any],
    token_env_default: str,
    user_env_default: str,
    password_env_default: str,
    default_auth_mode: str,
) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    mode = str(settings.get("auth_mode", default_auth_mode)).strip().lower()
    token_env = str(settings.get("token_env", token_env_default))
    user_env = str(settings.get("user_env", user_env_default))
    password_env = str(settings.get("password_env", password_env_default))

    if mode == "bearer":
        token = os.getenv(token_env, "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    if mode == "basic":
        username = os.getenv(user_env, "").strip()
        password = os.getenv(password_env, "").strip()
        if username and password:
            raw = f"{username}:{password}".encode("utf-8")
            encoded = base64.b64encode(raw).decode("ascii")
            headers["Authorization"] = f"Basic {encoded}"
        return headers

    return headers


def _http_get_json(url: str, *, headers: dict[str, str], timeout_seconds: float) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
    request = Request(url=url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            status = getattr(response, "status", 200)
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        return None, f"HTTP {exc.code}"
    except URLError as exc:
        return None, f"network error: {exc.reason}"
    except OSError as exc:
        return None, f"transport error: {exc}"

    if status < 200 or status >= 300:
        return None, f"HTTP {status}"

    if not body.strip():
        return None, "empty response"
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None, "invalid JSON response"
    if not isinstance(payload, (dict, list)):
        return None, "unexpected payload type"
    return payload, None
