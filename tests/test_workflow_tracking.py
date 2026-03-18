import pytest

from sdk_agent.core.workflow import SoftwareDeliveryWorkflow
from sdk_agent.web.tracker import InMemoryStatusTracker


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _Result:
    def __init__(self, output: str):
        self.final_output = output


class FakeRunner:
    def __init__(self, fail_on: str | None = None):
        self.calls = []
        self.fail_on = fail_on

    async def run(self, agent, prompt):
        self.calls.append((agent, prompt))
        if self.fail_on and self.fail_on == agent:
            raise RuntimeError("runner failure")
        return _Result(f"done:{agent}")


@pytest.mark.anyio
async def test_workflow_updates_tracker_for_all_stages():
    tracker = InMemoryStatusTracker()
    runner = FakeRunner()
    workflow = SoftwareDeliveryWorkflow(
        planner="planner-agent",
        developer="developer-agent",
        tester="tester-agent",
        reviewer="reviewer-agent",
        deployer="deployer-agent",
        status_tracker=tracker,
        runner=runner,
    )

    result = await workflow.run("Build feature X")

    assert result["run_id"] is not None
    assert result["plan"] == "done:planner-agent"
    assert result["implementation"] == "done:developer-agent"
    assert result["test_report"] == "done:tester-agent"
    assert result["review_report"] == "done:reviewer-agent"
    assert result["deploy_report"] == "done:deployer-agent"

    snapshot = tracker.snapshot()
    agent_by_name = {item["name"]: item for item in snapshot["agents"]}

    assert agent_by_name["planner"]["stage"] == "planning:completed"
    assert agent_by_name["developer"]["stage"] == "implementation:completed"
    assert agent_by_name["tester"]["stage"] == "testing:completed"
    assert agent_by_name["reviewer"]["stage"] == "review:completed"
    assert agent_by_name["deployer"]["stage"] == "deploy:completed"

    run = snapshot["runs"][0]
    assert run["status"] == "completed"


@pytest.mark.anyio
async def test_workflow_marks_skipped_stages_in_tracker():
    tracker = InMemoryStatusTracker()
    runner = FakeRunner()
    workflow = SoftwareDeliveryWorkflow(
        planner=None,
        developer="developer-agent",
        tester=None,
        reviewer="reviewer-agent",
        deployer=None,
        run_planning=False,
        run_testing=False,
        run_deploy=False,
        status_tracker=tracker,
        runner=runner,
    )

    result = await workflow.run("Fix bug Y")

    assert "planning" in result["skipped_stages"]
    assert "testing" in result["skipped_stages"]
    assert "deploy" in result["skipped_stages"]

    snapshot = tracker.snapshot()
    agent_by_name = {item["name"]: item for item in snapshot["agents"]}
    assert agent_by_name["planner"]["stage"] == "planning:skipped"
    assert agent_by_name["tester"]["stage"] == "testing:skipped"
    assert agent_by_name["deployer"]["stage"] == "deploy:skipped"


@pytest.mark.anyio
async def test_workflow_marks_run_failed_on_runner_error():
    tracker = InMemoryStatusTracker()
    runner = FakeRunner(fail_on="developer-agent")
    workflow = SoftwareDeliveryWorkflow(
        planner="planner-agent",
        developer="developer-agent",
        tester="tester-agent",
        reviewer="reviewer-agent",
        deployer="deployer-agent",
        status_tracker=tracker,
        runner=runner,
    )

    with pytest.raises(RuntimeError):
        await workflow.run("Break it")

    snapshot = tracker.snapshot()
    run = snapshot["runs"][0]
    assert run["status"] == "failed"
