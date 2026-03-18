from __future__ import annotations

import json
from types import SimpleNamespace
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import uuid4


class ApiStatusTracker:
    """Pushes agent status to a running SDK dashboard over HTTP."""

    def __init__(self, base_url: str, timeout: float = 3.0, fail_silently: bool = True):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.fail_silently = fail_silently

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict | None:
        data = None
        headers = {"Content-Type": "application/json"}

        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        request = Request(
            url=f"{self.base_url}{path}",
            data=data,
            method=method,
            headers=headers,
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except (HTTPError, URLError, TimeoutError, ValueError):
            if self.fail_silently:
                return None
            raise

    def register_agent(self, name: str):
        # Represent registration with a neutral status update.
        return self.update_agent(name=name, stage="idle", progress=0, message="registered")

    def register_agents(self, names):
        for name in names:
            self.register_agent(name)

    def start_run(self, request: str, run_id: str | None = None):
        effective_run_id = run_id or str(uuid4())
        payload = {"request": request, "run_id": effective_run_id}
        self._request("POST", "/api/runs/start", payload=payload)
        return SimpleNamespace(run_id=effective_run_id)

    def finish_run(self, run_id: str, status: str = "completed"):
        self._request("POST", f"/api/runs/{quote(run_id)}/finish?status={quote(status)}")
        return SimpleNamespace(run_id=run_id, status=status)

    def update_agent(self, name: str, stage: str, progress: int, message: str = ""):
        payload = {
            "stage": stage,
            "progress": progress,
            "message": message,
        }
        response = self._request("POST", f"/api/agents/{quote(name)}", payload=payload)
        return SimpleNamespace(**response) if isinstance(response, dict) else None

    def snapshot(self) -> dict:
        status = self._request("GET", "/api/status")
        if isinstance(status, dict):
            return status
        return {"agents": [], "runs": [], "timeline": []}
