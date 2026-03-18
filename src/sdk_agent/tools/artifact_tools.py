from __future__ import annotations

from pathlib import Path

from sdk_agent.context import ProjectContext
from sdk_agent.guardrails import ensure_path_within


def write_artifact(context: ProjectContext, task_id: str, name: str, content: str) -> Path:
    root = context.resolved_artifact_root()
    root.mkdir(parents=True, exist_ok=True)
    run_dir = ensure_path_within(root, root / task_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    target = ensure_path_within(run_dir, run_dir / name)
    target.write_text(content, encoding="utf-8")
    return target
