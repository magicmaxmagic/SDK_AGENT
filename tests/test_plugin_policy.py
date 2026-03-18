from pathlib import Path

from sdk_agent.plugins.critical_repo import CriticalRepoPlugin
from sdk_agent.plugins.generic import GenericProjectPlugin


def test_critical_plugin_quorum_policy() -> None:
    plugin = CriticalRepoPlugin(project_name="critical", repo_path=Path("."))
    context = plugin.to_context()
    assert context.required_staging_approvals == 2
    assert context.required_production_approvals == 4
    assert context.production_approval_validity_minutes == 60
    assert context.ticket_connector == "servicenow"


def test_generic_plugin_default_connector_and_quorum() -> None:
    plugin = GenericProjectPlugin(project_name="generic", repo_path=Path("."))
    context = plugin.to_context()
    assert context.required_staging_approvals == 2
    assert context.required_production_approvals == 3
    assert context.ticket_connector == "mock"
