from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sdk_agent.context import ProjectContext
from sdk_agent.core.artifacts import ArtifactManager
from sdk_agent.core.git_workflow import prepare_git_workflow
from sdk_agent.core.transitions import can_retry, should_rework_from_review, should_rework_from_validation
from sdk_agent.core.workflow_state import WorkflowStateStore
from sdk_agent.logging_config import get_logger
from sdk_agent.mcp import codex_mcp_server
from sdk_agent.models import FlowType, ReviewRecord, ValidationRecord, ValidationSummary, WorkflowState
from sdk_agent.plugins.base import BaseProjectPlugin
from sdk_agent.roles.reviewer import parse_review_findings
from sdk_agent.tools.git_tools import git_collect_changed_files, git_diff
from sdk_agent.tools.shell_tools import safe_run_command
from sdk_agent.tools.validation_tools import run_lint, run_tests

LOGGER = get_logger("workflow")


ROLE_CAPABILITIES: dict[str, dict[str, bool]] = {
    "planner": {"mcp": False, "shell": False, "write": False},
    "developer": {"mcp": True, "shell": True, "write": True},
    "tester": {"mcp": False, "shell": True, "write": False},
    "reviewer": {"mcp": False, "shell": False, "write": False},
    "release_manager": {"mcp": False, "shell": False, "write": False},
    "deployer": {"mcp": False, "shell": False, "write": False},
    "triage": {"mcp": False, "shell": False, "write": False},
}


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
    planner: Any
    developer: Any
    tester: Any
    reviewer: Any
    release_manager: Any
    deployer: Any
    triage: Any
    max_fix_iterations: int = 2
    runner: AgentsRunnerAdapter = field(default_factory=AgentsRunnerAdapter)

    async def run(
        self,
        flow: FlowType,
        request: str,
        branch_name: str | None = None,
        allow_commit: bool = False,
        allow_staging_deploy: bool = False,
        enable_tester_mcp: bool = False,
    ) -> WorkflowState:
        self.context.allow_staging_deploy = allow_staging_deploy
        state = WorkflowState.create(
            flow=flow,
            request=request,
            artifacts_path=self.context.resolved_artifact_root(),
            branch_name=branch_name,
        )
        state.artifacts_path = self.artifact_manager.run_dir(state.task_id)
        store = WorkflowStateStore(state)

        LOGGER.info(
            "workflow_started",
            extra={"extra_fields": {"task_id": state.task_id, "flow": flow.value, "branch": branch_name}},
        )

        try:
            if flow in {FlowType.FEATURE, FlowType.BUGFIX}:
                await self._run_feature_or_bugfix(
                    store=store,
                    allow_commit=allow_commit,
                    allow_staging_deploy=allow_staging_deploy,
                    enable_tester_mcp=enable_tester_mcp,
                )
            elif flow == FlowType.VALIDATE:
                await self._run_validate_only(store)
            elif flow == FlowType.REVIEW:
                await self._run_review_only(store)
            elif flow == FlowType.PLAN:
                await self._run_plan_only(store)
            else:
                raise ValueError(f"Unsupported flow: {flow}")
            state.complete()
        except Exception as exc:
            state.fail(str(exc))
            LOGGER.exception("workflow_failed", extra={"extra_fields": {"task_id": state.task_id}})

        self.artifact_manager.write_json(state.task_id, "final_summary.json", state.to_dict())
        LOGGER.info(
            "workflow_finished",
            extra={"extra_fields": {"task_id": state.task_id, "status": state.final_status.value}},
        )
        return state

    async def _run_plan_only(self, store: WorkflowStateStore) -> None:
        store.mark_phase("plan")
        plan = await self._role_run("planner", self.planner, self._planner_prompt(store.state.original_request))
        store.set_plan(plan)
        self.artifact_manager.write_text(store.state.task_id, "plan.md", plan)

    async def _run_validate_only(self, store: WorkflowStateStore) -> None:
        store.mark_phase("validate")
        validation = self._run_validation_commands()
        self._record_validation(store, validation)

        review_text = await self._role_run("reviewer", self.reviewer, self._review_prompt(store.state, "Validation-only run."))
        findings = parse_review_findings(review_text)
        self._record_review(store, findings)

        release_notes = await self._role_run("release_manager", self.release_manager, self._release_prompt(store.state))
        store.set_release_notes(release_notes)
        self.artifact_manager.write_text(store.state.task_id, "release_notes.md", release_notes)

    async def _run_review_only(self, store: WorkflowStateStore) -> None:
        store.mark_phase("review")
        diff_text = git_diff(self.context).stdout
        review_text = await self._role_run("reviewer", self.reviewer, self._review_prompt(store.state, diff_text))
        findings = parse_review_findings(review_text)
        self._record_review(store, findings)

        release_notes = await self._role_run("release_manager", self.release_manager, self._release_prompt(store.state))
        store.set_release_notes(release_notes)
        self.artifact_manager.write_text(store.state.task_id, "release_notes.md", release_notes)

    async def _run_feature_or_bugfix(
        self,
        store: WorkflowStateStore,
        allow_commit: bool,
        allow_staging_deploy: bool,
        enable_tester_mcp: bool,
    ) -> None:
        store.mark_phase("plan")
        plan = await self._role_run("planner", self.planner, self._planner_prompt(store.state.original_request))
        store.set_plan(plan)
        self.artifact_manager.write_text(store.state.task_id, "plan.md", plan)

        if self.context.dry_run:
            codex_context = _noop_async_context()
        else:
            codex_context = codex_mcp_server()

        async with codex_context as codex_server:
            if codex_server is not None:
                self._apply_role_mcp_access(enable_tester_mcp=enable_tester_mcp, codex_server=codex_server)
            else:
                self._apply_role_mcp_access(enable_tester_mcp=False, codex_server=None)

            while True:
                store.state.fix_iteration_count += 1
                store.mark_phase(f"implement_{store.state.fix_iteration_count}")
                implementation = await self._role_run("developer", self.developer, self._developer_prompt(store.state))
                self.artifact_manager.write_text(store.state.task_id, "implementation.md", implementation)

                changed_files = git_collect_changed_files(self.context)
                store.set_changed_files(changed_files)
                self.artifact_manager.write_json(store.state.task_id, "changed_files.json", {"files": changed_files})

                validation = self._run_validation_commands()
                self._record_validation(store, validation)
                if should_rework_from_validation(validation):
                    store.state.fix_iteration_reason = "validation_failed"
                    if can_retry(store.state, self.max_fix_iterations):
                        continue
                    raise RuntimeError("Validation failed after max fix iterations.")

                review_text = await self._role_run("reviewer", self.reviewer, self._review_prompt(store.state, git_diff(self.context).stdout))
                findings = parse_review_findings(review_text)
                self._record_review(store, findings)

                if should_rework_from_review(findings):
                    store.state.fix_iteration_reason = "blocking_review_findings"
                    if can_retry(store.state, self.max_fix_iterations):
                        continue
                    raise RuntimeError("Blocking review findings remain after max fix iterations.")
                break

        validation_summary = f"lint={store.state.lint_result.exit_code if store.state.lint_result else 'n/a'}, tests={store.state.test_result.exit_code if store.state.test_result else 'n/a'}"
        git_plan = prepare_git_workflow(
            context=self.context,
            request=store.state.original_request,
            branch_name=store.state.branch_name,
            create_branch=bool(store.state.branch_name),
            validation_summary=validation_summary,
        )
        store.state.branch_name = git_plan.branch_name
        self.artifact_manager.write_text(store.state.task_id, "pr_draft.md", git_plan.pr_body)
        self.artifact_manager.write_text(store.state.task_id, "commit_message.txt", git_plan.commit_message)

        if allow_commit:
            self._commit_changes(commit_message=git_plan.commit_message)

        release_notes = await self._role_run("release_manager", self.release_manager, self._release_prompt(store.state))
        store.set_release_notes(release_notes)
        self.artifact_manager.write_text(store.state.task_id, "release_notes.md", release_notes)

        if allow_staging_deploy and self.context.allow_staging_deploy:
            deploy_plan = await self._role_run("deployer", self.deployer, self._deploy_prompt(store.state))
            store.set_deploy_plan(deploy_plan)
            self.artifact_manager.write_text(store.state.task_id, "deploy_plan.md", deploy_plan)

    def _run_validation_commands(self) -> ValidationSummary:
        lint_result = run_lint(self.context)
        test_result = run_tests(self.context)
        return ValidationSummary(lint=lint_result, tests=test_result)

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
        self.artifact_manager.write_json(
            store.state.task_id,
            "lint_report.json",
            _command_result_to_dict(validation.lint) or {},
        )
        self.artifact_manager.write_json(
            store.state.task_id,
            "test_report.json",
            _command_result_to_dict(validation.tests) or {},
        )

    def _record_review(self, store: WorkflowStateStore, findings: list[Any]) -> None:
        store.state.review_findings = findings
        blocking_count = sum(1 for item in findings if item.blocking)
        store.state.review_history.append(
            ReviewRecord(
                timestamp=datetime.now(timezone.utc),
                findings=findings,
                blocking_count=blocking_count,
            )
        )
        self.artifact_manager.write_json(
            store.state.task_id,
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

    def _apply_role_mcp_access(self, enable_tester_mcp: bool, codex_server: object) -> None:
        if ROLE_CAPABILITIES["developer"]["mcp"] and codex_server is not None:
            self.developer.mcp_servers = [codex_server]
        else:
            self.developer.mcp_servers = []
        self.tester.mcp_servers = [codex_server] if (enable_tester_mcp and codex_server is not None) else []
        self.planner.mcp_servers = []
        self.reviewer.mcp_servers = []
        self.release_manager.mcp_servers = []
        self.deployer.mcp_servers = []

    async def _role_run(self, role: str, agent: Any, prompt: str) -> str:
        if self.context.dry_run:
            return self._dry_run_output(role=role, prompt=prompt)
        return await self.runner.run(agent, prompt)

    def _dry_run_output(self, role: str, prompt: str) -> str:
        if role == "reviewer":
            return "Dry-run review | low | none | false | No blocking findings in simulated mode"
        return f"[dry-run:{role}] simulated output for prompt length={len(prompt)}"

    def _commit_changes(self, commit_message: str) -> None:
        if "git add" not in self.context.allowed_commands:
            self.context.allowed_commands.extend(["git add", "git commit -m"])
        safe_run_command(self.context, "git add -A", role="developer")
        safe_run_command(self.context, f"git commit -m \"{commit_message}\"", role="developer")

    def _planner_prompt(self, request: str) -> str:
        rules = "\n".join(f"- {rule}" for rule in self.plugin.project_rules())
        return (
            f"Request:\n{request}\n\n"
            f"Repository: {self.context.repo_path}\n"
            "Create implementation plan with acceptance criteria, risks, and test strategy.\n"
            f"Project rules:\n{rules}"
        )

    def _developer_prompt(self, state: WorkflowState) -> str:
        findings = "\n".join(f"- {f.severity.value}: {f.title}" for f in state.review_findings) or "- none"
        return (
            f"Original request:\n{state.original_request}\n\n"
            f"Approved plan:\n{state.implementation_plan}\n\n"
            f"Known review findings:\n{findings}\n"
            "Make minimal safe changes and keep scope tight."
        )

    def _review_prompt(self, state: WorkflowState, diff_text: str) -> str:
        return (
            "Review repository changes as a strict reviewer. "
            "Use structured output lines:\n"
            "TITLE | SEVERITY | FILE_PATH_OR_NONE | BLOCKING(true/false) | RECOMMENDATION\n\n"
            f"Changed files: {state.changed_files}\n\n"
            f"Diff:\n{diff_text[:12000]}"
        )

    def _release_prompt(self, state: WorkflowState) -> str:
        return (
            "Prepare release notes with changed files, validation summary, risk section, and rollback checklist.\n"
            f"Changed files: {state.changed_files}\n"
            f"Lint exit: {state.lint_result.exit_code if state.lint_result else 'n/a'}\n"
            f"Test exit: {state.test_result.exit_code if state.test_result else 'n/a'}"
        )

    def _deploy_prompt(self, state: WorkflowState) -> str:
        return (
            "Prepare staging-only deployment steps using plugin deploy command. "
            "Never deploy production automatically. Include rollback and post-deploy checks.\n"
            f"Staging command: {self.context.deploy_staging_command or 'not configured'}\n"
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


class _noop_async_context:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return False
