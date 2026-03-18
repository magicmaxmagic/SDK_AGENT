from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


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

        return TicketValidationResult(False, "jira connector requires external client configuration", provider=self.name)


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

        return TicketValidationResult(False, "servicenow connector requires external client configuration", provider=self.name)


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
