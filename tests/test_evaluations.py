from pathlib import Path

from sdk_agent.core.evaluations import append_evaluation_index, build_evaluation_report, load_baseline_scores
from sdk_agent.models import AutonomyLevel, CommandResult, FlowType, TrustProfile, WorkflowState


def test_build_evaluation_report_penalizes_failures(tmp_path: Path) -> None:
    state = WorkflowState.create(
        flow=FlowType.FEATURE,
        request="Implement auth",
        artifacts_path=tmp_path,
        autonomy_level=AutonomyLevel.IMPLEMENT,
        trust_profile=TrustProfile.NORMAL_INTERNAL,
    )
    state.fix_iteration_count = 3
    state.errors = ["validation failed"]
    state.lint_result = CommandResult(command="lint", exit_code=1, stdout="", stderr="error")
    state.test_result = CommandResult(command="tests", exit_code=0, stdout="", stderr="")

    report = build_evaluation_report(state, baseline_scores=[0.9, 0.85])

    assert report["run_id"] == state.run_id
    assert report["score"]["value"] < 0.9
    assert report["baseline"]["samples"] == 2


def test_evaluation_index_roundtrip(tmp_path: Path) -> None:
    report_a = {
        "run_id": "run-a",
        "status": "completed",
        "score": {"value": 0.88, "grade": "good"},
    }
    report_b = {
        "run_id": "run-b",
        "status": "failed",
        "score": {"value": 0.41, "grade": "critical"},
    }

    append_evaluation_index(tmp_path, report_a)
    append_evaluation_index(tmp_path, report_b)

    baseline = load_baseline_scores(tmp_path)
    assert baseline == [0.88, 0.41]
