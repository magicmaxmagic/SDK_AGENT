from __future__ import annotations

from pathlib import Path

from sdk_agent.core.persistence import StatePersistence
from sdk_agent.models import WorkflowState


def save_workflow_state(run_dir: Path, state: WorkflowState) -> Path:
    return StatePersistence(run_dir=run_dir).save(state)


def load_workflow_state(run_dir: Path) -> WorkflowState:
    return StatePersistence(run_dir=run_dir).load()
