from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from sdk_agent.core.ticket_connectors import build_ticket_connector
from sdk_agent.logging_config import configure_logging
from sdk_agent.models import AutonomyLevel, FlowType, TrustProfile
from sdk_agent.plugins import CriticalRepoPlugin, GenericProjectPlugin, NextJsPlugin, PythonAppPlugin
from sdk_agent.team import build_team


PLUGIN_REGISTRY = {
    "generic": GenericProjectPlugin,
    "nextjs": NextJsPlugin,
    "python": PythonAppPlugin,
    "critical": CriticalRepoPlugin,
}


def _base_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SDK Agent autonomous engineering CLI", allow_abbrev=False)
    parser.add_argument("--repo-path", default=".")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--plugin", choices=sorted(PLUGIN_REGISTRY.keys()), default="generic")
    parser.add_argument("--model", default="gpt-5-codex")
    parser.add_argument("--artifacts-dir", default=".sdk_agent_runs")
    parser.add_argument("--autonomy-level", choices=[item.value for item in AutonomyLevel], default=None)
    parser.add_argument("--trust-profile", choices=[item.value for item in TrustProfile], default=None)
    parser.add_argument("--branch-name", default=None)
    parser.add_argument("--use-worktree", action="store_true")
    parser.add_argument("--allow-commit", action="store_true")
    parser.add_argument("--allow-pr-draft", action="store_true")
    parser.add_argument("--allow-staging-deploy", action="store_true")
    parser.add_argument("--allow-production-deploy", action="store_true")
    parser.add_argument("--production-approval-validity-minutes", type=int, default=120)
    parser.add_argument("--required-staging-approvals", type=int, default=2)
    parser.add_argument("--required-production-approvals", type=int, default=3)
    parser.add_argument("--ticket-connector", choices=["mock", "jira", "servicenow", "composite"], default=None)
    parser.add_argument("--ticket-connector-settings", default=None)
    parser.add_argument("--enable-tester-mcp", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-fix-iterations", type=int, default=2)

    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("feature", "bugfix", "plan"):
        cmd = sub.add_parser(name)
        cmd.add_argument("request")

    sub.add_parser("validate")
    sub.add_parser("review")

    resume = sub.add_parser("resume")
    resume.add_argument("--run-id", required=True)

    status = sub.add_parser("status")
    status.add_argument("--run-id", required=True)

    dep_staging = sub.add_parser("deploy-staging")
    dep_staging.add_argument("--run-id", required=True)

    dep_prod = sub.add_parser("deploy-production")
    dep_prod.add_argument("--run-id", required=True)

    approve_staging = sub.add_parser("approve-staging")
    approve_staging.add_argument("--run-id", required=True)
    approve_staging.add_argument("--approved-by", required=True)
    approve_staging.add_argument("--ticket", required=True)
    approve_staging.add_argument("--ticket-source", required=True)
    approve_staging.add_argument("--reason", required=True)
    approve_staging.add_argument("--expires-in-minutes", type=int, default=None)

    approve_prod = sub.add_parser("approve-production")
    approve_prod.add_argument("--run-id", required=True)
    approve_prod.add_argument("--approved-by", required=True)
    approve_prod.add_argument("--ticket", required=True)
    approve_prod.add_argument("--ticket-source", required=True)
    approve_prod.add_argument("--reason", required=True)
    approve_prod.add_argument("--expires-in-minutes", type=int, default=None)

    audit = sub.add_parser("audit")
    audit.add_argument("--run-id", required=True)
    audit.add_argument("--flat-fields", action="store_true")

    audit_verify = sub.add_parser("audit-verify-chain")
    audit_verify.add_argument("--run-id", required=True)
    audit_verify.add_argument("--skip-siem-exports", action="store_true")

    audit_export = sub.add_parser("audit-export-siem")
    audit_export.add_argument("--run-id", required=True)
    audit_export.add_argument("--flat-fields", action="store_true")
    audit_export.add_argument("--batch-size", type=int, default=500)
    audit_export.add_argument("--max-file-size-bytes", type=int, default=1_000_000)
    return parser


def _flow_from_command(command: str) -> FlowType:
    return {
        "feature": FlowType.FEATURE,
        "bugfix": FlowType.BUGFIX,
        "plan": FlowType.PLAN,
        "validate": FlowType.VALIDATE,
        "review": FlowType.REVIEW,
    }[command]


def _build_plugin(args: argparse.Namespace):
    plugin_cls = PLUGIN_REGISTRY[args.plugin]
    plugin = plugin_cls(
        project_name=args.project_name,
        repo_path=Path(args.repo_path).resolve(),
        artifact_root=Path(args.artifacts_dir),
    )

    if args.autonomy_level is not None:
        plugin.autonomy_level = lambda: AutonomyLevel(args.autonomy_level)
    if args.trust_profile is not None:
        plugin.trust_profile = lambda: TrustProfile(args.trust_profile)
    return plugin


async def _run_async(args: argparse.Namespace) -> int:
    plugin = _build_plugin(args)
    team = build_team(plugin=plugin, model=args.model, max_fix_iterations=args.max_fix_iterations)
    team.workflow.context.dry_run = args.dry_run
    team.workflow.context.production_approval_validity_minutes = args.production_approval_validity_minutes
    team.workflow.context.required_staging_approvals = args.required_staging_approvals
    team.workflow.context.required_production_approvals = args.required_production_approvals
    if args.ticket_connector is not None:
        team.workflow.context.ticket_connector = args.ticket_connector
    if args.ticket_connector_settings is not None:
        team.workflow.context.ticket_connector_settings = _parse_connector_settings(args.ticket_connector_settings)
    team.workflow.ticket_connector = build_ticket_connector(
        team.workflow.context.ticket_connector,
        team.workflow.context.ticket_connector_settings,
    )

    if args.command in {"feature", "bugfix", "plan", "validate", "review"}:
        request = getattr(args, "request", "") or f"{args.command} workflow"
        state = await team.workflow.run(
            flow=_flow_from_command(args.command),
            request=request,
            branch_name=args.branch_name,
            allow_commit=args.allow_commit,
            allow_staging_deploy=args.allow_staging_deploy,
            allow_production_deploy=args.allow_production_deploy,
            enable_tester_mcp=args.enable_tester_mcp,
            use_worktree=args.use_worktree,
        )
        print(json.dumps(state.to_dict(), indent=2, default=str))
        return 0

    if args.command == "resume":
        state = team.workflow.resume(run_id=args.run_id)
        print(json.dumps(state.to_dict(), indent=2, default=str))
        return 0

    if args.command == "status":
        state = team.workflow.status(run_id=args.run_id)
        print(json.dumps(state.to_dict(), indent=2, default=str))
        return 0

    if args.command == "deploy-staging":
        state = await team.workflow.deploy_staging(run_id=args.run_id)
        print(json.dumps(state.to_dict(), indent=2, default=str))
        return 0

    if args.command == "deploy-production":
        state = await team.workflow.deploy_production(run_id=args.run_id)
        print(json.dumps(state.to_dict(), indent=2, default=str))
        return 0

    if args.command == "approve-staging":
        state = team.workflow.approve_staging(
            run_id=args.run_id,
            approved_by=args.approved_by,
            ticket_id=args.ticket,
            ticket_source=args.ticket_source,
            reason=args.reason,
            expires_in_minutes=args.expires_in_minutes,
        )
        print(json.dumps(state.to_dict(), indent=2, default=str))
        return 0

    if args.command == "approve-production":
        state = team.workflow.approve_production(
            run_id=args.run_id,
            approved_by=args.approved_by,
            ticket_id=args.ticket,
            ticket_source=args.ticket_source,
            reason=args.reason,
            expires_in_minutes=args.expires_in_minutes,
        )
        print(json.dumps(state.to_dict(), indent=2, default=str))
        return 0

    if args.command == "audit":
        payload = team.workflow.read_audit(run_id=args.run_id, flat_fields=args.flat_fields)
        print(json.dumps(payload, indent=2, default=str))
        return 0

    if args.command == "audit-verify-chain":
        payload = team.workflow.verify_audit_chain(
            run_id=args.run_id,
            include_siem_exports=not args.skip_siem_exports,
        )
        print(json.dumps(payload, indent=2, default=str))
        return 0 if payload.get("valid") else 2

    if args.command == "audit-export-siem":
        paths = team.workflow.export_audit_siem_ndjson(
            run_id=args.run_id,
            flat_fields=args.flat_fields,
            batch_size=args.batch_size,
            max_file_size_bytes=args.max_file_size_bytes,
        )
        print(json.dumps({"files": [str(path) for path in paths]}, indent=2, default=str))
        return 0

    raise ValueError(f"Unsupported command: {args.command}")


def main() -> None:
    configure_logging()
    args = _base_parser().parse_args()
    raise SystemExit(asyncio.run(_run_async(args)))


def _parse_connector_settings(raw: str) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("--ticket-connector-settings must be a JSON object")
    return payload
