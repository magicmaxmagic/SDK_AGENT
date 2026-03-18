from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SDK Agent web dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    try:
        import uvicorn
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Uvicorn is missing. Install web extras: pip install -e '.[web]'"
        ) from exc

    uvicorn.run(
        "sdk_agent.web.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
