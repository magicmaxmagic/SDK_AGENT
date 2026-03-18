from __future__ import annotations

from datetime import datetime
from typing import Iterable
from uuid import uuid4

from sdk_agent.web.models import AgentStatus, TimelineEvent, WorkflowRun


class InMemoryStatusTracker:
    """Simple in-memory tracker for agent status and workflow progress."""

    def __init__(self, agent_names: Iterable[str] | None = None):
        self._agents: dict[str, AgentStatus] = {}
        self._timeline: list[TimelineEvent] = []
        self._runs: dict[str, WorkflowRun] = {}

        for name in agent_names or []:
            self.register_agent(name)

    def register_agent(self, name: str) -> AgentStatus:
        status = self._agents.get(name)
        if status is None:
            status = AgentStatus(name=name)
            self._agents[name] = status
            self._timeline.append(TimelineEvent(actor=name, message="registered"))
        return status

    def register_agents(self, names: Iterable[str]) -> None:
        for name in names:
            self.register_agent(name)

    def start_run(self, request: str, run_id: str | None = None) -> WorkflowRun:
        effective_run_id = run_id or str(uuid4())
        if effective_run_id in self._runs:
            raise ValueError(f"run_id already exists: {effective_run_id}")

        run = WorkflowRun(run_id=effective_run_id, request=request)
        self._runs[run.run_id] = run
        self._timeline.append(TimelineEvent(actor="workflow", message=f"run started: {run.run_id}"))
        return run

    def finish_run(self, run_id: str, status: str = "completed") -> WorkflowRun:
        run = self._runs[run_id]
        run.status = status
        run.finished_at = datetime.utcnow()
        self._timeline.append(TimelineEvent(actor="workflow", message=f"run {status}: {run.run_id}"))
        return run

    def update_agent(self, name: str, stage: str, progress: int, message: str = "") -> AgentStatus:
        status = self.register_agent(name)
        status.stage = stage
        status.progress = max(0, min(100, progress))
        status.message = message
        status.updated_at = datetime.utcnow()
        self._timeline.append(TimelineEvent(actor=name, message=f"{stage} ({status.progress}%) {message}".strip()))
        return status

    def snapshot(self) -> dict:
        return {
            "agents": [value.model_dump() for value in self._agents.values()],
            "runs": [value.model_dump() for value in self._runs.values()],
            "timeline": [value.model_dump() for value in self._timeline[-200:]],
        }
