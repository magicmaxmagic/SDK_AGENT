from sdk_agent.config import RoleConfig, TeamConfig, WorkflowConfig
from sdk_agent.context import ProjectContext
from sdk_agent.core.base_agent import BaseAgentFactory
from sdk_agent.plugins.backend import BackendProjectPlugin
from sdk_agent.plugins.portfolio import PortfolioProjectPlugin
from sdk_agent.team import build_software_team


def _fake_create(self, name: str, instructions: str, tools=None, handoffs=None):
    return {
        "name": name,
        "instructions": instructions,
        "tools": tools or [],
        "model": self.model,
        "handoffs": handoffs or [],
    }


def test_team_config_and_plugin_merge(monkeypatch):
    monkeypatch.setattr(BaseAgentFactory, "create", _fake_create)

    context = ProjectContext(
        project_name="portfolio",
        repo_path="/tmp/portfolio",
        notes=["Keep production stable", "Prefer incremental changes"],
    )

    plugin = PortfolioProjectPlugin(context=context)

    config = TeamConfig(
        model="gpt-5-codex",
        shared_tools=["repo_search"],
        roles={
            "developer": RoleConfig(
                instructions_suffix="Always include rollback-safe implementation notes.",
                tools=["config_dev_tool"],
            ),
        },
        workflow=WorkflowConfig(
            prompt_overrides={
                "testing": "CONFIG testing prompt override",
            }
        ),
    )

    team = build_software_team(
        context=context,
        developer_tools=["explicit_dev_tool"],
        team_config=config,
        plugins=[plugin],
    )

    developer = team["developer"]
    assert developer is not None
    assert developer["model"] == "gpt-5-codex"
    assert developer["tools"] == [
        "repo_search",
        "shell",
        "filesystem",
        "codex",
        "explicit_dev_tool",
        "config_dev_tool",
    ]
    assert "Preserve UX consistency" in developer["instructions"]
    assert "Always include rollback-safe implementation notes." in developer["instructions"]
    assert "Project notes:" in developer["instructions"]

    workflow = team["workflow"]
    assert workflow.prompt_overrides["testing"] == "CONFIG testing prompt override"


def test_role_disable_sets_agent_to_none(monkeypatch):
    monkeypatch.setattr(BaseAgentFactory, "create", _fake_create)

    context = ProjectContext(project_name="api", repo_path="/tmp/api")
    config = TeamConfig(
        roles={
            "reviewer": RoleConfig(enabled=False),
        }
    )

    team = build_software_team(context=context, team_config=config)

    assert team["reviewer"] is None
    assert team["workflow"].reviewer is None


def test_backend_plugin_framework_profiles(monkeypatch):
    monkeypatch.setattr(BaseAgentFactory, "create", _fake_create)

    context = ProjectContext(project_name="backend", repo_path="/tmp/backend")

    fastapi_team = build_software_team(
        context=context,
        plugins=[BackendProjectPlugin(context=context, framework="fastapi")],
    )
    django_team = build_software_team(
        context=context,
        plugins=[BackendProjectPlugin(context=context, framework="django")],
    )

    assert "FastAPI conventions" in fastapi_team["developer"]["instructions"]
    assert "Django conventions" in django_team["developer"]["instructions"]
    assert "migration plan" in fastapi_team["workflow"].prompt_overrides["deploy"]


def test_backend_plugin_rejects_invalid_framework():
    context = ProjectContext(project_name="backend", repo_path="/tmp/backend")
    plugin = BackendProjectPlugin(context=context, framework="flask")

    try:
        plugin.get_role_instruction_suffixes()
    except ValueError as exc:
        assert "framework must be either" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid backend framework")