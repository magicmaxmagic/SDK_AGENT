from sdk_agent.core.ticket_connectors import build_ticket_connector


def test_mock_connector_rejects_unknown_when_strict() -> None:
    connector = build_ticket_connector(
        "mock",
        {
            "allowed_sources": ["cab"],
            "ticket_pattern": r"^CHG-[0-9]{4}$",
            "strict_known": True,
            "known_tickets": {"cab": ["CHG-1234"]},
        },
    )

    rejected = connector.validate("CHG-9999", "cab")
    assert rejected.valid is False

    accepted = connector.validate("CHG-1234", "cab")
    assert accepted.valid is True


def test_composite_connector_routes_sources() -> None:
    connector = build_ticket_connector(
        "composite",
        {
            "allowed_sources": ["cab", "jira", "itsm"],
            "ticket_pattern": r"^(CHG|INC)-[0-9]{4}$",
        },
    )

    jira_result = connector.validate("CHG-1001", "jira")
    itsm_result = connector.validate("INC-9001", "itsm")

    assert jira_result.valid is False
    assert itsm_result.valid is False
    assert "requires external client configuration" in jira_result.reason
    assert "requires external client configuration" in itsm_result.reason
