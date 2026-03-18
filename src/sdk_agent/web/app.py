from __future__ import annotations

from html import escape

from sdk_agent.web.tracker import InMemoryStatusTracker

DASHBOARD_HTML = """<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>SDK Agent Monitor</title>
    <style>
      :root {
        --bg: #f4efe4;
        --surface: #fffdf7;
        --ink: #1f1b16;
        --accent: #2f6f54;
        --accent-2: #d8893b;
        --muted: #746a5f;
        --line: #d8cfc0;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: \"IBM Plex Sans\", \"Avenir Next\", \"Segoe UI\", sans-serif;
        color: var(--ink);
        background: radial-gradient(circle at 10% 10%, #efe6d4, transparent 35%),
                    radial-gradient(circle at 90% 90%, #f0dfca, transparent 30%),
                    var(--bg);
      }
      .shell { max-width: 1100px; margin: 0 auto; padding: 24px; }
      h1 { margin: 0; font-size: 2rem; letter-spacing: 0.01em; }
      .sub { color: var(--muted); margin-top: 8px; }
      .grid { display: grid; grid-template-columns: repeat(auto-fit,minmax(230px,1fr)); gap: 14px; margin-top: 20px; }
      .card {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 14px;
        box-shadow: 0 8px 24px rgba(31, 27, 22, 0.06);
      }
      .name { font-weight: 600; }
      .meta { font-size: 0.9rem; color: var(--muted); margin: 6px 0 10px; }
      .bar-wrap { background: #efe6d8; border-radius: 999px; height: 10px; overflow: hidden; }
      .bar { height: 10px; background: linear-gradient(90deg, var(--accent), var(--accent-2)); transition: width 0.35s ease; }
      .layout { display: grid; grid-template-columns: 1.3fr 1fr; gap: 16px; margin-top: 20px; }
      .timeline { max-height: 370px; overflow: auto; }
      .event { padding: 8px 0; border-bottom: 1px dashed var(--line); font-size: 0.92rem; }
      .event .actor { font-weight: 600; }
      .pill {
        display: inline-block;
        border-radius: 999px;
        padding: 3px 10px;
        font-size: 0.78rem;
        background: #e6f1eb;
        color: #205a44;
      }
      @media (max-width: 900px) {
        .layout { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <div class=\"shell\">
      <h1>SDK Agent Monitor</h1>
      <div class=\"sub\">Track live agent status and workflow progress</div>
      <div id=\"run-summary\" style=\"margin-top:14px\"></div>
      <section>
        <div class=\"grid\" id=\"agents\"></div>
      </section>
      <section class=\"layout\">
        <div class=\"card\">
          <div style=\"display:flex;justify-content:space-between;align-items:center\">
            <h3 style=\"margin:0\">Timeline</h3>
            <span class=\"pill\" id=\"event-count\">0 events</span>
          </div>
          <div class=\"timeline\" id=\"timeline\"></div>
        </div>
        <div class=\"card\">
          <h3 style=\"margin-top:0\">How to feed status</h3>
          <pre style=\"overflow:auto;font-size:.83rem;background:#f6f0e6;padding:10px;border-radius:8px\">POST /api/runs/start
POST /api/agents/{name}
body: {\"stage\":\"coding\",\"progress\":45,\"message\":\"Implementing auth\"}</pre>
        </div>
      </section>
    </div>
    <script>
      async function refresh() {
        const res = await fetch('/api/status');
        const data = await res.json();

        const runSummary = document.getElementById('run-summary');
        const running = data.runs.filter(r => r.status === 'running').length;
        runSummary.innerHTML = `<span class=\"pill\">${running} run(s) in progress</span>`;

        const agents = document.getElementById('agents');
        agents.innerHTML = data.agents.map(a => `
          <div class=\"card\">
            <div class=\"name\">${a.name}</div>
            <div class=\"meta\">${a.stage} · ${a.progress}%</div>
            <div class=\"bar-wrap\"><div class=\"bar\" style=\"width:${a.progress}%\"></div></div>
            <div class=\"meta\" style=\"margin-top:8px\">${a.message || ''}</div>
          </div>
        `).join('');

        const timeline = document.getElementById('timeline');
        timeline.innerHTML = [...data.timeline].reverse().map(e => `
          <div class=\"event\"><span class=\"actor\">${e.actor}</span> · ${e.message}</div>
        `).join('');
        document.getElementById('event-count').textContent = `${data.timeline.length} events`;
      }
      refresh();
      setInterval(refresh, 2000);
    </script>
  </body>
</html>"""


def create_dashboard_app(tracker: InMemoryStatusTracker | None = None):
    try:
        from fastapi import FastAPI
        from fastapi import HTTPException
        from fastapi.responses import HTMLResponse
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "FastAPI dependencies are missing. Install with: pip install 'sdk-agent[web]'"
        ) from exc

    tracker = tracker or InMemoryStatusTracker(
        agent_names=["planner", "developer", "tester", "reviewer", "deployer"]
    )

    app = FastAPI(title="SDK Agent Monitor", version="0.1.0")

    @app.get("/")
    async def dashboard():
        return HTMLResponse(content=DASHBOARD_HTML)

    @app.get("/api/status")
    async def get_status():
        return tracker.snapshot()

    @app.post("/api/runs/start")
    async def start_run(payload: dict):
        raw_request = payload.get("request")
        run_id = payload.get("run_id")

        if not isinstance(raw_request, str):
            raise HTTPException(status_code=400, detail="request must be a string")
        if run_id is not None and not isinstance(run_id, str):
            raise HTTPException(status_code=400, detail="run_id must be a string")

        try:
            run = tracker.start_run(request=escape(raw_request), run_id=run_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        return run.model_dump()

    @app.post("/api/runs/{run_id}/finish")
    async def finish_run(run_id: str, status: str = "completed"):
        if status not in {"completed", "failed", "cancelled"}:
            raise HTTPException(status_code=400, detail="invalid status")

        try:
            run = tracker.finish_run(run_id=run_id, status=status)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="run not found") from exc

        return run.model_dump()

    @app.post("/api/agents/{agent_name}")
    async def update_agent(agent_name: str, payload: dict):
        stage = payload.get("stage")
        progress = payload.get("progress")
        message = payload.get("message", "")

        if not isinstance(stage, str):
            raise HTTPException(status_code=400, detail="stage must be a string")
        if not isinstance(progress, int):
            raise HTTPException(status_code=400, detail="progress must be an integer")
        if not isinstance(message, str):
            raise HTTPException(status_code=400, detail="message must be a string")

        status = tracker.update_agent(
            name=agent_name,
            stage=stage,
            progress=progress,
            message=message,
        )
        return status.model_dump()

    app.state.tracker = tracker
    return app
