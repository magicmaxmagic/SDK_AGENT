from __future__ import annotations

import argparse
import asyncio
import json

from sdk_agent.context import ProjectContext
from sdk_agent.mcp import codex_mcp_server
from sdk_agent.team import build_software_team


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run sdk_agent workflow")
    parser.add_argument("task", help="Task description for the agent team")
    parser.add_argument("--project-name", default="portfolio")
    parser.add_argument("--repo-path", default=".")
    parser.add_argument("--model", default="gpt-5-codex")
    parser.add_argument("--test-command", default="npm test")
    parser.add_argument("--lint-command", default="npm run lint")
    parser.add_argument("--deploy-staging-command", default="./scripts/deploy_staging.sh")
    return parser


async def _run(args: argparse.Namespace) -> int:
    context = ProjectContext(
        project_name=args.project_name,
        repo_path=args.repo_path,
        test_command=args.test_command,
        lint_command=args.lint_command,
        deploy_staging_command=args.deploy_staging_command,
        notes=["Never deploy to production automatically."],
    )

    async with codex_mcp_server() as codex_server:
        team = build_software_team(
            context=context,
            model=args.model,
            mcp_servers=[codex_server],
        )
        result = await team["workflow"].run(args.task)

    print(json.dumps(result, indent=2, default=str))
    return 0


def main() -> None:
    args = _parser().parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
