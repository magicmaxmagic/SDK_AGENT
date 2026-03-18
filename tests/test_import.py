from sdk_agent import ProjectContext, build_software_team
from sdk_agent.core.base_agent import BaseAgentFactory


def _fake_create(self, name: str, instructions: str, mcp_servers=None, tools=None, handoffs=None):
    return {
        "name": name,
        "instructions": instructions,
        "mcp_servers": mcp_servers or [],
        "tools": tools or [],
        "handoffs": handoffs or [],
    }


def test_import_and_build_team(monkeypatch):
    monkeypatch.setattr(BaseAgentFactory, "create", _fake_create)

    context = ProjectContext(
        project_name="test_project",
        repo_path="/tmp/test_project",
    )

    team = build_software_team(context=context, model="gpt-5-codex", mcp_servers=None)

    assert "planner" in team
    assert "developer" in team
    assert "tester" in team
    assert "reviewer" in team
    assert "deployer" in team
    assert "workflow" in team
