from pathlib import Path

from sdk_agent.plugins import GenericProjectPlugin, NextJsPlugin, PythonAppPlugin


def test_plugin_context_values() -> None:
    next_plugin = NextJsPlugin(project_name="web", repo_path=Path("/tmp/web"))
    py_plugin = PythonAppPlugin(project_name="api", repo_path=Path("/tmp/api"))
    generic = GenericProjectPlugin(project_name="misc", repo_path=Path("/tmp/misc"))

    assert next_plugin.to_context().lint_command == "npm run lint"
    assert py_plugin.to_context().test_command == "pytest -q"
    assert "git status" in generic.to_context().allowed_commands
