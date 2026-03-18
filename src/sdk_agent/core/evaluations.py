from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from sdk_agent.models import WorkflowState


@dataclass(slots=True)
class ReliabilityScore:
    value: float
    grade: str


def build_evaluation_report(state: WorkflowState, baseline_scores: list[float] | None = None) -> dict[str, Any]:
    baseline = baseline_scores or []
    penalties = _collect_penalties(state)
    score_value = max(0.0, 1.0 - sum(item["amount"] for item in penalties))
    score = ReliabilityScore(value=round(score_value, 3), grade=_score_grade(score_value))

    baseline_avg = round(mean(baseline), 3) if baseline else None
    drift_delta = round(score.value - baseline_avg, 3) if baseline_avg is not None else None

    return {
        "run_id": state.run_id,
        "score": {"value": score.value, "grade": score.grade},
        "status": state.final_status.value,
        "fix_iteration_count": state.fix_iteration_count,
        "penalties": penalties,
        "baseline": {
            "samples": len(baseline),
            "average": baseline_avg,
            "drift_delta": drift_delta,
            "drift_detected": drift_delta is not None and drift_delta < -0.2,
        },
    }


def load_baseline_scores(artifact_root: Path, *, limit: int = 20) -> list[float]:
    index_file = artifact_root / "evaluations_index.json"
    if not index_file.exists():
        return []
    try:
        payload = json.loads(index_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    items = payload.get("runs", []) if isinstance(payload, dict) else []
    scores: list[float] = []
    for item in items[-limit:]:
        if not isinstance(item, dict):
            continue
        score_payload = item.get("score", {})
        if not isinstance(score_payload, dict):
            continue
        value = score_payload.get("value")
        if isinstance(value, (int, float)):
            scores.append(float(value))
    return scores


def append_evaluation_index(artifact_root: Path, report: dict[str, Any]) -> Path:
    index_file = artifact_root / "evaluations_index.json"
    payload = {"runs": []}
    if index_file.exists():
        try:
            loaded = json.loads(index_file.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and isinstance(loaded.get("runs"), list):
                payload = loaded
        except (OSError, json.JSONDecodeError):
            payload = {"runs": []}

    payload["runs"] = [item for item in payload.get("runs", []) if isinstance(item, dict) and item.get("run_id") != report.get("run_id")]
    payload["runs"].append({
        "run_id": report.get("run_id"),
        "status": report.get("status"),
        "score": report.get("score", {}),
    })

    index_file.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    return index_file


def _collect_penalties(state: WorkflowState) -> list[dict[str, Any]]:
    penalties: list[dict[str, Any]] = []

    lint_failed = state.lint_result is not None and state.lint_result.exit_code != 0
    tests_failed = state.test_result is not None and state.test_result.exit_code != 0
    if lint_failed or tests_failed:
        penalties.append({"name": "validation_failed", "amount": 0.35})

    if any(_is_blocking(item) for item in state.review_findings):
        penalties.append({"name": "review_blocking_findings", "amount": 0.2})

    if any(_is_blocking(item) for item in state.security_findings):
        penalties.append({"name": "security_blocking_findings", "amount": 0.25})

    if state.fix_iteration_count > 1:
        penalties.append({"name": "retry_iterations", "amount": min(0.2, 0.05 * state.fix_iteration_count)})

    if state.errors:
        penalties.append({"name": "runtime_errors", "amount": 0.1})

    return penalties


def _is_blocking(item: Any) -> bool:
    if isinstance(item, dict):
        return bool(item.get("blocking", False))
    return bool(getattr(item, "blocking", False))


def _score_grade(value: float) -> str:
    if value >= 0.9:
        return "excellent"
    if value >= 0.75:
        return "good"
    if value >= 0.5:
        return "warning"
    return "critical"
