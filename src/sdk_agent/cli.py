from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from sdk_agent.logging_config import configure_logging
from sdk_agent.models import FlowType
from sdk_agent.plugins import GenericProjectPlugin, NextJsPlugin, PythonAppPlugin
from sdk_agent.team import build_team


PLUGIN_REGISTRY = {
    "generic": GenericProjectPlugin,
    "nextjs": NextJsPlugin,
    "python": PythonAppPlugin,
}


def _base_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SDK Agent engineering workflow CLI")
    parser.add_argument("--repo-path", default=".", help="Repository path to operate in")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--plugin", choices=sorted(PLUGIN_REGISTRY.keys()), default="generic")
    parser.add_argument("--model", default="gpt-5-codex")
    parser.add_argument("--artifacts-dir", default=".sdk_agent_runs")
    parser.add_argument("--max-fix-iterations", type=int, default=2)

    sub = parser.add_subparsers(dest="command", required=True)

    for cmd in ("feature", "bugfix", "plan"):
        p = sub.add_parser(cmd)
        p.add_argument("request")

    sub.add_parser("validate")
    sub.add_parser("review")
    return parser


def _flow_from_command(command: str) -> FlowType:
    mapping = {
        "feature": FlowType.FEATURE,
        "bugfix": FlowType.BUGFIX,
        "plan": FlowType.PLAN,
        "validate": FlowType.VALIDATE,
        "review": FlowType.REVIEW,
    }
    return mapping[command]


async def _run_async(args: argparse.Namespace) -> int:
    plugin_cls = PLUGIN_REGISTRY[args.plugin]
    plugin = plugin_cls(
        project_name=args.project_name,
        repo_path=Path(args.repo_path).resolve(),
        artifact_root=Path(args.artifacts_dir),
    )

    team = build_team(plugin=plugin, model=args.model, max_fix_iterations=args.max_fix_iterations)

    request = getattr(args, "request", "") or f"{args.command} workflow"
    state = await team.workflow.run(flow=_flow_from_command(args.command), request=request)
    print(json.dumps(state.to_dict(), indent=2, default=str))
    return 0


def main() -> None:
    configure_logging()
    parser = _base_parser()
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run_async(args)))
