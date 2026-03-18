from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator

from sdk_agent.context import ProjectContext
from sdk_agent.core.artifacts import ArtifactManager
from sdk_agent.core.audit import AuditLogger
from sdk_agent.core.git_workflow import prepare_git_workflow
from sdk_agent.core.persistence import StatePersistence
from sdk_agent.core.policy_engine import PolicyEngine
from sdk_agent.core.sensitivity import classify_sensitive_changes
from sdk_agent.core.transitions import can_retry, should_rework_from_review, should_rework_from_validation
from sdk_agent.core.workflow_state import WorkflowStateStore
from sdk_agent.logging_config import get_logger
from sdk_agent.mcp import codex_mcp_server
from sdk_agent.models import (
    ActionType,
    AutonomyLevel,
    FlowType,
    ReviewRecord,
    RoleName,
    ValidationRecord,
    ValidationSummary,
    WorkflowState,
    WorkflowStatus,
)
from sdk_agent.plugins.base import BaseProjectPlugin
from sdk_agent.roles.reviewer import parse_review_findings
from sdk_agent.tools.git_tools import git_collect_changed_files, git_diff
from sdk_agent.tools.shell_tools import safe_run_command
from sdk_agent.tools.validation_tools import run_lint, run_tests

LOGGER = get_logger("workflow")


class AgentsRunnerAdapter:
    async def run(self, agent: Any, prompt: str) -> str:
        from agents import Runner

        result = await Runner.run(agent, prompt)
        return str(result.final_output)


@dataclass(slots=True)
class WorkflowEngine:
    context: ProjectContext
    plugin: BaseProjectPlugin
    artifact_manager: ArtifactManager
    audit_logger: AuditLogger
    policy_engine: PolicyEngine
    triage: Any
    planner: Any
    architect: Any
    developer: Any
    tester: Any
    reviewer: Any
    security_reviewer: Any
    release_manager: Any
    deployer: Any
    policy_enforcer: Any
    max_fix_iterations: int = 2
    runner: AgentsRunnerAdapter = field(default_factory=AgentsRunnerAdapter)

    async def run(
        self,
        flow: FlowType,
        request: str,
        branch_name: str | None = None,
        allow_commit: bool = False,
        allow_staging_deploy: bool = False,
        allow_production_deploy: bool = False,
        enable_tester_mcp: bool = False,
        use_worktree: bool = False,
        run_id: str | None = None,
    ) -> WorkflowState:
        if run_id:
            return self.resume(run_id=run_id)

        self.context.allow_staging_deploy = allow_staging_deploy
        self.context.allow_production_deploy = allow_production_deploy
        self.context.use_worktree = use_worktree

        state = WorkflowState.create(
            flow=flow,
            request=request,
            artifacts_path=self.context.resolved_artifact_root(),
            autonomy_level=self.context.autonomy_level,
            trust_profile=self.context.trust_profile,
            branch_name=branch_name,
        )
        state.human_approval_required = True
        state.artifacts_path = self.artifact_manager.run_dir(state.run_id)
        self.audit_logger = AuditLogger(run_dir=state.artifacts_path)
        persistence = StatePersistence(run_dir=state.artifacts_path)
        store = WorkflowStateStore(state)

        self.audit_logger.record("workflow_started", {"run_id": state.run_id, "flow": flow.value})
        persistence.save(state)

        try:
            if flow in {FlowType.FEATURE, FlowType.BUGFIX}:
                await self._run_feature_or_bugfix(store, allow_commit=allow_commit, enable_tester_mcp=enable_tester_mcp)
            elif flow == FlowType.PLAN:
                await self._run_plan(store)
            elif flow == FlowType.VALIDATE:
                await self._run_validate(store)
            elif flow == FlowType.REVIEW:
                await self._run_review(store)
            else:
                raise ValueError(f"Unsupported flow: {flow}")

            state.complete()
        except PermissionError as exc:
            state.block(str(exc))
        except Exception as exc:
            state.fail(str(exc))
            LOGGER.exception("workflow_failed", extra={"extra_fields": {"run_id": state.run_id}})

        persistence.save(state)
        self.artifact_manager.write_json(state.run_id, "state.json", state.to_dict())
        self.artifact_manager.write_json(state.run_id, "final_summary.json", state.to_dict())
        self.audit_logger.record("workflow_finished", {"run_id": state.run_id, "status": state.final_status.value})
        return state

    def resume(self, run_id: str) -> WorkflowState:
        run_dir = self.context.resolved_artifact_root() / run_id
        persistence = StatePersistence(run_dir=run_dir)
        state = persistence.load()
        state.add_event("resumed")
        self.audit_logger = AuditLogger(run_dir=run_dir)
        self.audit_logger.record("workflow_resumed", {"run_id": run_id, "phase": state.current_phase})
        persistence.save(state)
        return state

    def status(self, run_id: str) -> WorkflowState:
        run_dir = self.context.resolved_artifact_root() / run_id
        return StatePersistence(run_dir=run_dir).load()

    def read_audit(self, run_id: str) -> list[dict[str, Any]]:
        run_dir = self.context.resolved_artifact_root() / run_id
        return AuditLogger(run_dir=run_dir).read_all()

    async def deploy_staging(self, run_id: str) -> WorkflowState:
        state = self.status(run_id)
        decision = self.policy_engine.evaluate(ActionType.DEPLOY_STAGING, RoleName.DEPLOYER)
        state.add_policy_decision(decision)
        if not decision.allowed:
            state.block(decision.reason)
            self._persist_state(state)
            return state

        if state.final_status not in {WorkflowStatus.COMPLETED, WorkflowStatus.RUNNING}:
            state.block("staging deploy requires successful workflow state")
            self._persist_state(state)
            return state

        if not state.deploy_plan:
            deploy_plan = await self._role_run(RoleName.DEPLOYER, self.deployer, self._deploy_prompt(state, target="staging"))
            state.deploy_plan = deploy_plan
            self.artifact_manager.write_text(state.run_id, "deploy_plan.md", deploy_plan)

        self.audit_logger = AuditLogger(run_dir=self.context.resolved_artifact_root() / run_id)
        self.audit_logger.record("deploy_staging_prepared", {"run_id": run_id}, role=RoleName.DEPLOYER.value, action=ActionType.DEPLOY_STAGING.value)

        deploy_result = self._execute_deploy_command(target="staging")
        state.deployment_history.append(
            {
                "target": "staging",
                "command": self.context.deploy_staging_command,
                "exit_code": deploy_result.exit_code,
                "stdout": deploy_result.stdout,
                "stderr": deploy_result.stderr,
            }
        )
        if deploy_result.exit_code != 0:
            state.rollback_required("staging deployment failed; triggering automatic rollback")
            self.audit_logger.record(
                "deploy_staging_failed",
                {"run_id": run_id, "exit_code": deploy_result.exit_code},
                status="failure",
                role=RoleName.DEPLOYER.value,
                action=ActionType.DEPLOY_STAGING.value,
            )
            self._run_automatic_rollback(state, target="staging", cause=deploy_result.stderr or deploy_result.stdout)
        else:
            self.audit_logger.record(
                "deploy_staging_succeeded",
                {"run_id": run_id, "exit_code": deploy_result.exit_code},
                status="success",
                role=RoleName.DEPLOYER.value,
                action=ActionType.DEPLOY_STAGING.value,
            )
            state.add_event("deploy:staging:succeeded")

        self._persist_state(state)
        return state

    def approve_production(self, run_id: str, approved_by: str, ticket_id: str, reason: str) -> WorkflowState:
        state = self.status(run_id)
        state.human_approval_required = False
        state.production_approval = {
            "approved_by": approved_by,
            "ticket_id": ticket_id,
            "reason": reason,
            "approved_at": datetime.now(timezone.utc).isoformat(),
        }
        self.audit_logger = AuditLogger(run_dir=self.context.resolved_artifact_root() / run_id)
        self.audit_logger.record(
            "policy_production_approved",
            {"run_id": run_id, "approved_by": approved_by, "ticket_id": ticket_id},
            status="success",
            role=RoleName.POLICY_ENFORCER.value,
            action=ActionType.DEPLOY_PRODUCTION.value,
        )
        self._persist_state(state)
        return state

    async def deploy_production(self, run_id: str) -> WorkflowState:
        state = self.status(run_id)
        decision = self.policy_engine.evaluate(ActionType.DEPLOY_PRODUCTION, RoleName.DEPLOYER)
        state.add_policy_decision(decision)
        if not decision.allowed:
            state.block(decision.reason)
            self._persist_state(state)
            return state

        if state.human_approval_required or not state.production_approval:
            state.block("human approval required before production deploy")
            self.audit_logger = AuditLogger(run_dir=self.context.resolved_artifact_root() / run_id)
            self.audit_logger.record(
                "policy_production_approval_missing",
                {"run_id": run_id},
                status="failure",
                role=RoleName.POLICY_ENFORCER.value,
                action=ActionType.DEPLOY_PRODUCTION.value,
            )
            self._persist_state(state)
            return state

        if not state.rollback_plan:
            state.rollback_plan = "Prepare rollback by redeploying previous healthy release and verifying health checks."
            self.artifact_manager.write_text(state.run_id, "rollback_plan.md", state.rollback_plan)

        self.audit_logger = AuditLogger(run_dir=self.context.resolved_artifact_root() / run_id)
        self.audit_logger.record("deploy_production_candidate", {"run_id": run_id}, role=RoleName.DEPLOYER.value, action=ActionType.DEPLOY_PRODUCTION.value)

        deploy_result = self._execute_deploy_command(target="production")
        state.deployment_history.append(
            {
                "target": "production",
                "command": self.context.deploy_production_command,
                "exit_code": deploy_result.exit_code,
                "stdout": deploy_result.stdout,
                "stderr": deploy_result.stderr,
                "approved_by": state.production_approval.get("approved_by") if state.production_approval else None,
                "approval_ticket": state.production_approval.get("ticket_id") if state.production_approval else None,
            }
        )
        if deploy_result.exit_code != 0:
            state.rollback_required("production deployment failed; triggering automatic rollback")
            self.audit_logger.record(
                "deploy_production_failed",
                {"run_id": run_id, "exit_code": deploy_result.exit_code},
                status="failure",
                role=RoleName.DEPLOYER.value,
                action=ActionType.DEPLOY_PRODUCTION.value,
            )
            self._run_automatic_rollback(state, target="production", cause=deploy_result.stderr or deploy_result.stdout)
        else:
            self.audit_logger.record(
                "deploy_production_succeeded",
                {"run_id": run_id, "exit_code": deploy_result.exit_code},
                status="success",
                role=RoleName.DEPLOYER.value,
                action=ActionType.DEPLOY_PRODUCTION.value,
            )
            state.add_event("deploy:production:succeeded")

        self._persist_state(state)
        return state

    async def _run_plan(self, store: WorkflowStateStore) -> None:
        store.mark_phase("plan")
        store.state.checkpoint("plan")
        plan = await self._role_run(RoleName.PLANNER, self.planner, self._planner_prompt(store.state.original_request))
        store.set_plan(plan)
        self.artifact_manager.write_text(store.state.run_id, "plan.md", plan)
        self._persist_state(store.state)

    async def _run_validate(self, store: WorkflowStateStore) -> None:
        store.mark_phase("validate")
        validation = self._run_validation_commands(store.state)
        self._record_validation(store, validation)
        review_text = await self._role_run(RoleName.REVIEWER, self.reviewer, self._review_prompt(store.state, "validation-only"))
        findings = parse_review_findings(review_text)
        self._record_review(store, findings)
        self._persist_state(store.state)

    async def _run_review(self, store: WorkflowStateStore) -> None:
        store.mark_phase("review")
        diff_text = git_diff(self.context).stdout
        review_text = await self._role_run(RoleName.REVIEWER, self.reviewer, self._review_prompt(store.state, diff_text))
        findings = parse_review_findings(review_text)
        self._record_review(store, findings)
        release_notes = await self._role_run(RoleName.RELEASE_MANAGER, self.release_manager, self._release_prompt(store.state))
        store.set_release_notes(release_notes)
        self.artifact_manager.write_text(store.state.run_id, "release_notes.md", release_notes)
        self._persist_state(store.state)

    async def _run_feature_or_bugfix(self, store: WorkflowStateStore, allow_commit: bool, enable_tester_mcp: bool) -> None:
        store.mark_phase("triage")
        triage_output = await self._role_run(RoleName.TRIAGE, self.triage, f"Classify and sequence workflow for request: {store.state.original_request}")
        self.audit_logger.record("triage", {"output": triage_output[:500]})

        store.mark_phase("plan")
        plan = await self._role_run(RoleName.PLANNER, self.planner, self._planner_prompt(store.state.original_request))
        store.set_plan(plan)
        self.artifact_manager.write_text(store.state.run_id, "plan.md", plan)

        store.mark_phase("architecture")
        architecture = await self._role_run(RoleName.ARCHITECT, self.architect, self._architect_prompt(store.state))
        self.artifact_manager.write_text(store.state.run_id, "architecture_review.md", architecture)

        async with self._codex_context() as codex_server:
            self._apply_role_mcp_access(enable_tester_mcp, codex_server)

            while True:
                store.state.fix_iteration_count += 1
                store.state.checkpoint(f"implementation_{store.state.fix_iteration_count}")
                implementation = await self._role_run(RoleName.DEVELOPER, self.developer, self._developer_prompt(store.state))
                self.artifact_manager.write_text(store.state.run_id, "implementation.md", implementation)

                changed_files = git_collect_changed_files(self.context)
                store.set_changed_files(changed_files)
                self.artifact_manager.write_json(store.state.run_id, "changed_files.json", {"files": changed_files})

                sensitive = classify_sensitive_changes(changed_files)
                self.artifact_manager.write_json(
                    store.state.run_id,
                    "sensitivity_report.json",
                    {
                        "sensitive_files": sensitive.sensitive_files,
                        "categories": sensitive.categories,
                        "requires_security_review": sensitive.requires_security_review,
                    },
                )

                validation = self._run_validation_commands(store.state)
                self._record_validation(store, validation)
                if should_rework_from_validation(validation):
                    store.set_fix_iteration_reason("validation_failed")
                    if can_retry(store.state, self.max_fix_iterations):
                        continue
                    raise RuntimeError("validation failed after maximum retries")

                review_text = await self._role_run(RoleName.REVIEWER, self.reviewer, self._review_prompt(store.state, git_diff(self.context).stdout))
                findings = parse_review_findings(review_text)
                self._record_review(store, findings)

                if sensitive.requires_security_review:
                    security_output = await self._role_run(
                        RoleName.SECURITY_REVIEWER,
                        self.security_reviewer,
                        self._security_prompt(store.state, sensitive.categories),
                    )
                    security_findings = parse_review_findings(security_output)
                    self._record_security_review(store.state, security_findings)
                    if any(item.blocking for item in security_findings):
                        store.set_fix_iteration_reason("security_review_blocked")
                        if can_retry(store.state, self.max_fix_iterations):
                            continue
                        raise RuntimeError("security review has blocking findings")

                if should_rework_from_review(findings):
                    store.set_fix_iteration_reason("review_blocked")
                    if can_retry(store.state, self.max_fix_iterations):
                        continue
                    raise RuntimeError("review has blocking findings")
                break

        validation_summary = f"lint={store.state.lint_result.exit_code if store.state.lint_result else 'n/a'}, tests={store.state.test_result.exit_code if store.state.test_result else 'n/a'}"
        git_plan = prepare_git_workflow(
            context=self.context,
            request=store.state.original_request,
            branch_name=store.state.branch_name,
            create_branch=bool(store.state.branch_name),
            validation_summary=validation_summary,
            use_worktree=self.context.use_worktree,
            run_id=store.state.run_id,
        )
        store.state.branch_name = git_plan.branch_name
        store.state.worktree_path = git_plan.worktree_path
        self.artifact_manager.write_text(store.state.run_id, "pr_draft.md", git_plan.pr_body)
        self.artifact_manager.write_text(store.state.run_id, "commit_message.txt", git_plan.commit_message)
        self.artifact_manager.write_text(store.state.run_id, "diff_summary.md", git_plan.diff_summary)

        if allow_commit:
            commit_decision = self.policy_engine.evaluate(ActionType.COMMIT, RoleName.DEVELOPER)
            store.state.add_policy_decision(commit_decision)
            if commit_decision.allowed:
                self._commit_changes(git_plan.commit_message)

        release_notes = await self._role_run(RoleName.RELEASE_MANAGER, self.release_manager, self._release_prompt(store.state))
        store.set_release_notes(release_notes)
        self.artifact_manager.write_text(store.state.run_id, "release_notes.md", release_notes)

        deploy_plan = await self._role_run(RoleName.DEPLOYER, self.deployer, self._deploy_prompt(store.state, target="staging"))
        store.set_deploy_plan(deploy_plan)
        self.artifact_manager.write_text(store.state.run_id, "deploy_plan.md", deploy_plan)

        rollback_plan = "Rollback: redeploy previous stable build, run smoke checks, and verify key metrics."
        store.state.rollback_plan = rollback_plan
        self.artifact_manager.write_text(store.state.run_id, "rollback_plan.md", rollback_plan)
        self._persist_state(store.state)

    def _run_validation_commands(self, state: WorkflowState) -> ValidationSummary:
        lint_decision = self.policy_engine.evaluate(ActionType.RUN_SHELL, RoleName.TESTER)
        state.add_policy_decision(lint_decision)
        if not lint_decision.allowed:
            raise PermissionError(lint_decision.reason)

        lint_result = run_lint(self.context)
        tests_result = run_tests(self.context)
        return ValidationSummary(lint=lint_result, tests=tests_result)

    def _record_validation(self, store: WorkflowStateStore, validation: ValidationSummary) -> None:
        store.state.lint_result = validation.lint
        store.state.test_result = validation.tests
        store.state.validation_history.append(
            ValidationRecord(
                timestamp=datetime.now(timezone.utc),
                lint=validation.lint,
                tests=validation.tests,
                passed=validation.passed,
            )
        )
        self.artifact_manager.write_json(store.state.run_id, "lint_report.json", _command_result_to_dict(validation.lint) or {})
        self.artifact_manager.write_json(store.state.run_id, "test_report.json", _command_result_to_dict(validation.tests) or {})

    def _record_review(self, store: WorkflowStateStore, findings: list[Any]) -> None:
        store.state.review_findings = findings
        blocking_count = sum(1 for item in findings if item.blocking)
        store.state.review_history.append(
            ReviewRecord(timestamp=datetime.now(timezone.utc), findings=findings, blocking_count=blocking_count)
        )
        self.artifact_manager.write_json(
            store.state.run_id,
            "review_report.json",
            {
                "findings": [
                    {
                        "title": item.title,
                        "severity": item.severity.value,
                        "file_path": item.file_path,
                        "recommendation": item.recommendation,
                        "blocking": item.blocking,
                        "details": item.details,
                    }
                    for item in findings
                ]
            },
        )

    def _record_security_review(self, state: WorkflowState, findings: list[Any]) -> None:
        self.artifact_manager.write_json(
            state.run_id,
            "security_review.json",
            {
                "findings": [
                    {
                        "title": item.title,
                        "severity": item.severity.value,
                        "file_path": item.file_path,
                        "recommendation": item.recommendation,
                        "blocking": item.blocking,
                        "details": item.details,
                    }
                    for item in findings
                ]
            },
        )

    def _apply_role_mcp_access(self, enable_tester_mcp: bool, codex_server: object | None) -> None:
        self.developer.mcp_servers = [codex_server] if codex_server is not None else []
        self.tester.mcp_servers = [codex_server] if (enable_tester_mcp and codex_server is not None) else []
        self.planner.mcp_servers = []
        self.architect.mcp_servers = []
        self.reviewer.mcp_servers = []
        self.security_reviewer.mcp_servers = []
        self.release_manager.mcp_servers = []
        self.deployer.mcp_servers = []

    def _commit_changes(self, commit_message: str) -> None:
        if "git add" not in self.context.allowed_commands:
            self.context.allowed_commands.extend(["git add", "git commit -m"])
        safe_run_command(self.context, "git add -A", role=RoleName.DEVELOPER.value)
        safe_run_command(self.context, f"git commit -m \"{commit_message}\"", role=RoleName.DEVELOPER.value)

    def _execute_deploy_command(self, target: str):
        if target == "staging":
            command = self.context.deploy_staging_command
        else:
            command = self.context.deploy_production_command

        if not command:
            from sdk_agent.models import CommandResult

            return CommandResult(
                command="none",
                exit_code=0,
                stdout=f"No {target} deployment command configured; prepared plan only.",
                stderr="",
            )
        return safe_run_command(self.context, command, role=RoleName.DEPLOYER.value)

    def _run_automatic_rollback(self, state: WorkflowState, target: str, cause: str) -> None:
        rollback_action = ActionType.ROLLBACK_STAGING if target == "staging" else ActionType.ROLLBACK_PRODUCTION
        rollback_command = (
            self.context.rollback_staging_command if target == "staging" else self.context.rollback_production_command
        )
        rollback_decision = self.policy_engine.evaluate(rollback_action, RoleName.DEPLOYER)
        state.add_policy_decision(rollback_decision)

        if not rollback_decision.allowed:
            state.rollback_history.append(
                {
                    "target": target,
                    "status": "blocked",
                    "reason": rollback_decision.reason,
                    "cause": cause,
                }
            )
            self.audit_logger.record(
                f"rollback_{target}_blocked",
                {"run_id": state.run_id, "reason": rollback_decision.reason},
                status="failure",
                role=RoleName.DEPLOYER.value,
                action=rollback_action.value,
            )
            return

        if not rollback_command:
            state.rollback_history.append(
                {
                    "target": target,
                    "status": "missing_command",
                    "reason": "rollback command not configured",
                    "cause": cause,
                }
            )
            self.audit_logger.record(
                f"rollback_{target}_missing_command",
                {"run_id": state.run_id},
                status="failure",
                role=RoleName.DEPLOYER.value,
                action=rollback_action.value,
            )
            return

        rollback_result = safe_run_command(self.context, rollback_command, role=RoleName.DEPLOYER.value)
        rollback_entry = {
            "target": target,
            "command": rollback_command,
            "exit_code": rollback_result.exit_code,
            "stdout": rollback_result.stdout,
            "stderr": rollback_result.stderr,
            "cause": cause,
        }
        state.rollback_history.append(rollback_entry)
        self.artifact_manager.write_json(state.run_id, f"rollback_{target}_result.json", rollback_entry)

        event_name = f"rollback_{target}_{'succeeded' if rollback_result.exit_code == 0 else 'failed'}"
        self.audit_logger.record(
            event_name,
            {"run_id": state.run_id, "exit_code": rollback_result.exit_code},
            status="success" if rollback_result.exit_code == 0 else "failure",
            role=RoleName.DEPLOYER.value,
            action=rollback_action.value,
        )

    def _persist_state(self, state: WorkflowState) -> None:
        StatePersistence(run_dir=state.artifacts_path).save(state)
        self.artifact_manager.write_json(state.run_id, "state.json", state.to_dict())

    async def _role_run(self, role: RoleName, agent: Any, prompt: str) -> str:
        action = self._role_action(role)
        decision = self.policy_engine.evaluate(action, role)
        self.audit_logger.record("policy_check", {"role": role.value, "allowed": decision.allowed, "reason": decision.reason})
        if not decision.allowed:
            raise PermissionError(f"policy denied {role.value}: {decision.reason}")
        if self.context.dry_run:
            return self._dry_run_output(role=role, prompt=prompt)
        return await self.runner.run(agent, prompt)

    def _role_action(self, role: RoleName) -> ActionType:
        mapping = {
            RoleName.DEVELOPER: ActionType.EDIT_FILE,
            RoleName.TESTER: ActionType.RUN_SHELL,
            RoleName.DEPLOYER: ActionType.DEPLOY_STAGING,
            RoleName.RELEASE_MANAGER: ActionType.CREATE_PR_DRAFT,
        }
        return mapping.get(role, ActionType.CREATE_BRANCH)

    def _dry_run_output(self, role: RoleName, prompt: str) -> str:
        if role in {RoleName.REVIEWER, RoleName.SECURITY_REVIEWER}:
            return "Dry run finding | low | none | false | No blocking findings in simulation"
        return f"[dry-run:{role.value}] simulated output for prompt length={len(prompt)}"

    @asynccontextmanager
    async def _codex_context(self) -> AsyncIterator[object | None]:
        if self.context.dry_run:
            yield None
            return

        async with codex_mcp_server() as server:
            yield server

    def _planner_prompt(self, request: str) -> str:
        return f"Create a plan with acceptance criteria, risks, and validation strategy for request: {request}"

    def _architect_prompt(self, state: WorkflowState) -> str:
        return f"Review architecture for plan:\n{state.implementation_plan}"

    def _developer_prompt(self, state: WorkflowState) -> str:
        return f"Implement request with minimal safe changes:\n{state.original_request}\nPlan:\n{state.implementation_plan}"

    def _review_prompt(self, state: WorkflowState, diff_text: str) -> str:
        return (
            "Review changes with strict structured format: "
            "TITLE | SEVERITY | FILE_PATH_OR_NONE | BLOCKING(true/false) | RECOMMENDATION\n"
            f"Changed files: {state.changed_files}\nDiff:\n{diff_text[:12000]}"
        )

    def _security_prompt(self, state: WorkflowState, categories: list[str]) -> str:
        return (
            "Security review required. Output structured findings format. "
            f"Sensitive categories: {categories}. Changed files: {state.changed_files}"
        )

    def _release_prompt(self, state: WorkflowState) -> str:
        return (
            "Prepare release notes with risk summary, validation results, and rollback checklist.\n"
            f"Lint exit: {state.lint_result.exit_code if state.lint_result else 'n/a'}\n"
            f"Test exit: {state.test_result.exit_code if state.test_result else 'n/a'}"
        )

    def _deploy_prompt(self, state: WorkflowState, target: str) -> str:
        return (
            f"Prepare deployment plan for {target}. Include health checks, rollback strategy, and verification steps.\n"
            f"Changed files: {state.changed_files}"
        )


def _command_result_to_dict(result: Any) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "command": result.command,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
