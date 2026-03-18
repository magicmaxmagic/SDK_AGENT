from datetime import datetime
from pydantic import BaseModel, Field


class AgentStatus(BaseModel):
    name: str
    stage: str = "idle"
    progress: int = 0
    message: str = ""
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WorkflowRun(BaseModel):
    run_id: str
    request: str
    status: str = "running"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None


class TimelineEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor: str
    message: str
