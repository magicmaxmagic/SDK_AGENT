from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sdk_agent.context import ProjectContext
from sdk_agent.guardrails import ensure_path_within


@dataclass(slots=True)
class ArtifactManager:
    context: ProjectContext

    def run_dir(self, task_id: str) -> Path:
        root = self.context.resolved_artifact_root()
        root.mkdir(parents=True, exist_ok=True)
        task_dir = ensure_path_within(root, root / task_id)
        task_dir.mkdir(parents=True, exist_ok=True)
        return task_dir

    def write_text(self, task_id: str, name: str, content: str) -> Path:
        target = ensure_path_within(self.run_dir(task_id), self.run_dir(task_id) / name)
        target.write_text(content, encoding="utf-8")
        return target

    def write_json(self, task_id: str, name: str, payload: dict[str, Any]) -> Path:
        target = ensure_path_within(self.run_dir(task_id), self.run_dir(task_id) / name)
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
        return target
