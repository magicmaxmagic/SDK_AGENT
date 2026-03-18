import pytest

from sdk_agent.web.app import create_dashboard_app
from sdk_agent.web.tracker import InMemoryStatusTracker


@pytest.fixture()
def client():
    fastapi = pytest.importorskip("fastapi")
    testclient = pytest.importorskip("fastapi.testclient")

    tracker = InMemoryStatusTracker(agent_names=["planner"])
    app = create_dashboard_app(tracker=tracker)
    return testclient.TestClient(app)


def test_dashboard_root_available(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "SDK Agent Monitor" in response.text


def test_start_run_escapes_html_payload(client):
    payload = {"request": "<script>alert(1)</script>", "run_id": "safe-1"}

    response = client.post("/api/runs/start", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["request"] == "&lt;script&gt;alert(1)&lt;/script&gt;"


def test_start_run_duplicate_id_returns_conflict(client):
    payload = {"request": "run", "run_id": "dup-1"}

    first = client.post("/api/runs/start", json=payload)
    second = client.post("/api/runs/start", json=payload)

    assert first.status_code == 200
    assert second.status_code == 409


def test_finish_unknown_run_returns_404(client):
    response = client.post("/api/runs/missing/finish")

    assert response.status_code == 404


def test_finish_invalid_status_returns_400(client):
    client.post("/api/runs/start", json={"request": "run", "run_id": "r2"})

    response = client.post("/api/runs/r2/finish?status=evil")

    assert response.status_code == 400


def test_agent_update_progress_clamped(client):
    response = client.post(
        "/api/agents/developer",
        json={"stage": "coding", "progress": 999, "message": "ok"},
    )

    assert response.status_code == 200
    assert response.json()["progress"] == 100
