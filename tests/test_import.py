from sdk_agent import build_software_team, ProjectContext


def test_import_and_build_team():
    context = ProjectContext(
        project_name="test_project",
        repo_path="/tmp/test_project",
    )

    team = build_software_team(context=context)

    assert "planner" in team
    assert "developer" in team
    assert "tester" in team
    assert "reviewer" in team
    assert "deployer" in team
    assert "workflow" in team
