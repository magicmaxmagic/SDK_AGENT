from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

from sdk_agent import ProjectContext, TeamConfig, WorkflowConfig, build_software_team
from sdk_agent.plugins.portfolio import PortfolioProjectPlugin
from sdk_agent.web import ApiStatusTracker, InMemoryStatusTracker


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run SDK agent team on a portfolio repository")
    parser.add_argument("request", help="Development request for the agent workflow")
    parser.add_argument(
        "--executor",
        choices=["agents-sdk", "codex-cli"],
        default="agents-sdk",
        help="Execution backend: agents-sdk (Python orchestration) or codex-cli (terminal Codex workflow).",
    )
    parser.add_argument("--repo-path", default="/home/maxence/Documents/portfolio")
    parser.add_argument("--project-name", default="portfolio")
    parser.add_argument("--model", default=os.getenv("SDK_AGENT_MODEL", "gpt-5-codex"))
    parser.add_argument(
        "--use-local-codex",
        action="store_true",
        help="Use local Codex/OpenAI-compatible endpoint and bypass required cloud API key.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("OPENAI_BASE_URL"),
        help="OpenAI-compatible API base URL (example: http://127.0.0.1:11434/v1).",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("OPENAI_API_KEY"),
        help="API key for the configured endpoint. For local mode a dummy key is accepted.",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List models from the configured endpoint and exit.",
    )
    parser.add_argument(
        "--disable-tracing",
        action="store_true",
        help="Disable agent tracing export (useful for local endpoints).",
    )
    parser.add_argument(
        "--dashboard-url",
        default=os.getenv("SDK_AGENT_DASHBOARD_URL", "http://127.0.0.1:8000"),
        help="Dashboard base URL for live status sync.",
    )
    parser.add_argument(
        "--no-dashboard-sync",
        action="store_true",
        help="Disable dashboard synchronization and keep status local to this process.",
    )
    parser.add_argument("--test-command", default="npm test")
    parser.add_argument("--lint-command", default="npm run lint")
    parser.add_argument("--enable-deploy", action="store_true")
    parser.add_argument(
        "--auto-commit",
        action="store_true",
        help="Automatically git add/commit all repository changes at the end of a successful run.",
    )
    parser.add_argument(
        "--auto-push",
        action="store_true",
        help="Automatically git push after a successful run (uses --push-remote and --push-branch).",
    )
    parser.add_argument(
        "--commit-message",
        default="chore: apply sdk-agent automated changes",
        help="Commit message used when --auto-commit is enabled.",
    )
    parser.add_argument(
        "--push-remote",
        default="origin",
        help="Git remote used when --auto-push is enabled.",
    )
    parser.add_argument(
        "--push-branch",
        default=None,
        help="Git branch used when --auto-push is enabled (defaults to current branch).",
    )
    parser.add_argument("--max-iterations", type=int, default=5)
    parser.add_argument("--no-require-approval", action="store_true")
    parser.add_argument(
        "--notes",
        nargs="*",
        default=["Preserve existing UX and routes", "Prefer minimal incremental changes"],
    )
    return parser


def _configure_runtime_credentials(args: argparse.Namespace) -> tuple[str | None, str | None]:
    base_url = args.base_url
    api_key = args.api_key

    if args.use_local_codex:
        if not base_url:
            base_url = os.getenv("CODEX_BASE_URL", "http://127.0.0.1:11434/v1")
        if not api_key:
            api_key = "local-codex-key"

    if not api_key:
        print(
            "Error: no API key found. Set OPENAI_API_KEY, pass --api-key, or use --use-local-codex.",
            file=sys.stderr,
        )
        return None, None

    os.environ["OPENAI_API_KEY"] = api_key
    if base_url:
        os.environ["OPENAI_BASE_URL"] = base_url

    return base_url, api_key


def _build_status_tracker(args: argparse.Namespace):
    if args.no_dashboard_sync:
        return InMemoryStatusTracker(agent_names=["planner", "developer", "tester", "reviewer", "deployer"])

    return ApiStatusTracker(base_url=args.dashboard_url, fail_silently=True)


def _git_run(args: argparse.Namespace, git_args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", args.repo_path, *git_args],
        check=False,
        capture_output=True,
        text=True,
    )


def _maybe_auto_git_actions(args: argparse.Namespace) -> tuple[int, dict]:
    if not args.auto_commit and not args.auto_push:
        return 0, {"enabled": False}

    git_info: dict[str, object] = {
        "enabled": True,
        "auto_commit": args.auto_commit,
        "auto_push": args.auto_push,
        "committed": False,
        "pushed": False,
    }

    in_repo = _git_run(args, ["rev-parse", "--is-inside-work-tree"])
    if in_repo.returncode != 0 or in_repo.stdout.strip() != "true":
        print(
            f"Error: --auto-commit/--auto-push requires a git repository at {args.repo_path}.",
            file=sys.stderr,
        )
        return 3, git_info

    status = _git_run(args, ["status", "--porcelain"])
    has_changes = bool(status.stdout.strip())
    git_info["has_worktree_changes"] = has_changes

    if args.auto_commit:
        if has_changes:
            add_all = _git_run(args, ["add", "-A"])
            if add_all.returncode != 0:
                print("Error: git add failed during auto-commit.", file=sys.stderr)
                if add_all.stderr.strip():
                    print(add_all.stderr.strip(), file=sys.stderr)
                return 3, git_info

            commit = _git_run(args, ["commit", "-m", args.commit_message])
            if commit.returncode != 0:
                print("Error: git commit failed during auto-commit.", file=sys.stderr)
                if commit.stderr.strip():
                    print(commit.stderr.strip(), file=sys.stderr)
                return 3, git_info

            git_info["committed"] = True
            git_info["commit_message"] = args.commit_message
        else:
            git_info["commit_skipped"] = "no_changes"

    if args.auto_push:
        target_branch = args.push_branch
        if target_branch is None:
            branch = _git_run(args, ["rev-parse", "--abbrev-ref", "HEAD"])
            if branch.returncode != 0:
                print("Error: unable to determine current branch for auto-push.", file=sys.stderr)
                return 3, git_info
            target_branch = branch.stdout.strip()
            if target_branch == "HEAD":
                print(
                    "Error: detached HEAD detected. Use --push-branch to set an explicit branch.",
                    file=sys.stderr,
                )
                return 3, git_info

        push = _git_run(args, ["push", args.push_remote, target_branch])
        if push.returncode != 0:
            print("Error: git push failed during auto-push.", file=sys.stderr)
            if push.stderr.strip():
                print(push.stderr.strip(), file=sys.stderr)
            return 3, git_info

        git_info["pushed"] = True
        git_info["push_remote"] = args.push_remote
        git_info["push_branch"] = target_branch

    return 0, git_info


def _run_codex_cli_workflow(args: argparse.Namespace, tracker) -> int:
    codex_path = shutil.which("codex")
    if codex_path is None:
        print("Error: codex CLI is not installed or not available in PATH.", file=sys.stderr)
        return 2

    tracker.register_agents(["planner", "developer", "tester", "reviewer", "deployer"])
    run = tracker.start_run(request=args.request)

    stages = [
        (
            "PLAN",
            (
                "Read AGENTS.md and the repository. "
                f"Create a concise implementation plan for this task: {args.request}"
            ),
        ),
        (
            "IMPLEMENT",
            (
                "Implement this task with the smallest safe diff: "
                f"{args.request}. Reuse existing patterns and do not change unrelated files."
            ),
        ),
        (
            "VALIDATE",
            (
                f"Run validation commands and report outcomes. Use test command '{args.test_command}' "
                f"and lint command '{args.lint_command}'. If failure is caused by your changes, fix it."
            ),
        ),
        (
            "REVIEW",
            (
                "Review current changes for bugs, regressions, edge cases, maintainability issues, and missing tests."
            ),
        ),
        (
            "DEPLOY PREP",
            (
                "Prepare staging deployment steps, rollback steps, and post-deploy verification checklist. "
                "Never deploy to production automatically."
            ),
        ),
    ]

    stage_agent = {
        "PLAN": ("planner", "planning"),
        "IMPLEMENT": ("developer", "implementation"),
        "VALIDATE": ("tester", "testing"),
        "REVIEW": ("reviewer", "review"),
        "DEPLOY PREP": ("deployer", "deploy"),
    }

    for stage_name, prompt in stages:
        agent_name, stage_key = stage_agent[stage_name]
        print(f"== {stage_name} ==")
        tracker.update_agent(agent_name, f"{stage_key}:running", 10, "started")
        completed = subprocess.run([codex_path, prompt], cwd=args.repo_path)
        if completed.returncode != 0:
            tracker.update_agent(agent_name, f"{stage_key}:failed", 100, f"exit_code={completed.returncode}")
            tracker.finish_run(run.run_id, status="failed")
            print(
                f"Error: codex step '{stage_name}' failed with exit code {completed.returncode}.",
                file=sys.stderr,
            )
            return completed.returncode
        tracker.update_agent(agent_name, f"{stage_key}:completed", 100, "done")

    git_rc, git_info = _maybe_auto_git_actions(args)
    if git_rc != 0:
        tracker.finish_run(run.run_id, status="failed")
        return git_rc

    tracker.finish_run(run.run_id, status="completed")

    print(
        json.dumps(
            {
                "executor": "codex-cli",
                "repo_path": args.repo_path,
                "request": args.request,
                "status": "completed",
                "run_id": run.run_id,
                "git": git_info,
            },
            indent=2,
        )
    )
    return 0


def _fetch_available_models(base_url: str, api_key: str) -> list[str]:
    request = Request(
        url=f"{base_url.rstrip('/')}/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )

    try:
        with urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError):
        return []

    data = payload.get("data", []) if isinstance(payload, dict) else []
    models = [item.get("id") for item in data if isinstance(item, dict)]
    return [model for model in models if isinstance(model, str) and model.strip()]


def _configure_tracing(args: argparse.Namespace) -> None:
    should_disable = args.disable_tracing or args.use_local_codex
    if not should_disable:
        return

    try:
        from agents.tracing import set_tracing_disabled

        set_tracing_disabled(True)
    except Exception:
        # Tracing config is best effort and should not block workflow execution.
        return


def _resolve_model(args: argparse.Namespace, base_url: str | None, api_key: str | None) -> str | None:
    if not base_url or not api_key:
        return args.model

    available_models = _fetch_available_models(base_url=base_url, api_key=api_key)

    if args.list_models:
        if not available_models:
            print("No models discovered from endpoint or endpoint is unreachable.", file=sys.stderr)
            return None
        print("Available models:")
        for model in available_models:
            print(f"- {model}")
        return None

    if args.use_local_codex and available_models and args.model not in available_models:
        fallback_model = os.getenv("CODEX_MODEL") or available_models[0]
        print(
            f"Warning: model '{args.model}' not found on local endpoint. Using '{fallback_model}' instead.",
            file=sys.stderr,
        )
        return fallback_model

    return args.model


async def _run_workflow(args: argparse.Namespace) -> int:
    if not os.path.isdir(args.repo_path):
        print(f"Error: repository path does not exist: {args.repo_path}", file=sys.stderr)
        return 2

    tracker = _build_status_tracker(args)

    if args.executor == "codex-cli":
        return _run_codex_cli_workflow(args, tracker)

    base_url, _api_key = _configure_runtime_credentials(args)
    if _api_key is None:
        return 2

    _configure_tracing(args)
    resolved_model = _resolve_model(args, base_url=base_url, api_key=_api_key)
    if resolved_model is None:
        return 0

    context = ProjectContext(
        project_name=args.project_name,
        repo_path=args.repo_path,
        test_command=args.test_command,
        lint_command=args.lint_command,
        notes=args.notes + [f"Target repository path: {args.repo_path}"],
    )

    plugin = PortfolioProjectPlugin(context=context)

    config = TeamConfig(
        model=resolved_model,
        workflow=WorkflowConfig(
            run_deploy=args.enable_deploy,
            max_iterations=max(1, args.max_iterations),
            require_approval=not args.no_require_approval,
        ),
    )

    team = build_software_team(
        context=context,
        team_config=config,
        plugins=[plugin],
        status_tracker=tracker,
    )

    result = await team["workflow"].run(args.request)
    git_rc, git_info = _maybe_auto_git_actions(args)
    if git_rc != 0:
        return git_rc

    snapshot = tracker.snapshot()

    output = {
        "request": args.request,
        "repo_path": args.repo_path,
        "model": resolved_model,
        "base_url": base_url,
        "local_codex_mode": args.use_local_codex,
        "dashboard_url": None if args.no_dashboard_sync else args.dashboard_url,
        "max_iterations": max(1, args.max_iterations),
        "require_approval": not args.no_require_approval,
        "result": result,
        "git": git_info,
        "agent_status": snapshot["agents"],
        "runs": snapshot["runs"],
    }
    print(json.dumps(output, indent=2, default=str))
    return 0


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run_workflow(args)))


if __name__ == "__main__":
    main()
