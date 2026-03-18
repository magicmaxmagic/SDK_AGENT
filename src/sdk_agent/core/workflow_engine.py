from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sdk_agent.context import ProjectContext
from sdk_agent.core.artifacts import ArtifactManager
from sdk_agent.core.transitions import can_retry, should_rework_from_review, should_rework_from_validation
from sdk_agent.core.workflow_state import WorkflowStateStore
from sdk_agent.logging_config import get_logger
from sdk_agent.mcp import codex_mcp_server
from sdk_agent.models import (
    CommandResult,
    FlowType,
    ReviewFinding,
    Severity,
    ValidationSummary,
    WorkflowState,
)
from sdk_agent.plugins.base import BaseProjectPlugin
from sdk_agent.tools.artifact_tools import write_artifact
from sdk_agent.tools.git_tools import collect_changed_files
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
    planner: Any
    developer: Any
    tester: Any
    reviewer: Any
    release_manager: Any
    deployer: Any
    triage: Any
    max_fix_iterations: int = 2
    runner: AgentsRunnerAdapter = AgentsRunnerAdapter()

    async def run(self, flow: FlowType, request: str) -> WorkflowState:
        state = WorkflowState.create(
            flow=flow,
            request=request,
            artifacts_path=self.context.resolved_artifact_root(),
        )
        state.artifacts_path = self.artifact_manager.run_dir(state.task_id)
        store = WorkflowStateStore(state)

        LOGGER.info("workflow_started", extra={"extra_fields": {"task_id": state.task_id, "flow": flow.value}})

        try:
            if flow in {FlowType.FEATURE, FlowType.BUGFIX}:
                await self._run_feature_or_bugfix(store)
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
        prompt = self._planner_prompt(store.state.original_request)
        plan = await self.runner.run(self.planner, prompt)
        store.set_plan(plan)
        write_artifact(self.context, store.state.task_id, "plan.md", plan)

    async def _run_validate_only(self, store: WorkflowStateStore) -> None:
        store.mark_phase("validate")
        validation = self._run_validation_commands()
        self._update_validation_state(store, validation)
        review_text = await self.runner.run(
            self.reviewer,
            self._review_prompt(store.state, "Validation-only risk summary."),
        )
        findings = self._parse_review_text(review_text)
        store.state.review_findings = findings
        write_artifact(self.context, store.state.task_id, "review_report.md", review_text)

    async def _run_review_only(self, store: WorkflowStateStore) -> None:
        store.mark_phase("review")
        diff = self._safe_git_diff()
        review_text = await self.runner.run(self.reviewer, self._review_prompt(store.state, diff))
        findings = self._parse_review_text(review_text)
        store.state.review_findings = findings
        write_artifact(self.context, store.state.task_id, "review_report.md", review_text)

        release_notes = await self.runner.run(
            self.release_manager,
            self._release_prompt(store.state),
        )
        store.set_release_notes(release_notes)
        write_artifact(self.context, store.state.task_id, "release_notes.md", release_notes)

    async def _run_feature_or_bugfix(self, store: WorkflowStateStore) -> None:
        store.mark_phase("plan")
        plan = await self.runner.run(self.planner, self._planner_prompt(store.state.original_request))
        store.set_plan(plan)
        write_artifact(self.context, store.state.task_id, "plan.md", plan)

        async with codex_mcp_server() as codex_server:
            self.developer.mcp_servers = [codex_server]
            self.tester.mcp_servers = [codex_server]

            while True:
                store.state.iteration += 1
                store.mark_phase(f"implementation_{store.state.iteration}")
                implement_text = await self.runner.run(
                    self.developer,
                    self._developer_prompt(store.state),
                )
                write_artifact(self.context, store.state.task_id, "implementation.md", implement_text)

                changed = collect_changed_files(self.context)
                store.set_changed_files(changed)

                validation = self._run_validation_commands()
                self._update_validation_state(store, validation)
                if should_rework_from_validation(validation):
                    if can_retry(store.state, self.max_fix_iterations):
                        continue
                    raise RuntimeError("Validation failed after max fix iterations.")

                review_text = await self.runner.run(
                    self.reviewer,
                    self._review_prompt(store.state, self._safe_git_diff()),
                )
                findings = self._parse_review_text(review_text)
                store.state.review_findings = findings
                write_artifact(self.context, store.state.task_id, "review_report.md", review_text)

                if should_rework_from_review(findings):
                    if can_retry(store.state, self.max_fix_iterations):
                        continue
                    raise RuntimeError("Critical review findings remain after max fix iterations.")
                break

        store.mark_phase("release")
        release_notes = await self.runner.run(self.release_manager, self._release_prompt(store.state))
        deploy_plan = await self.runner.run(self.deployer, self._deploy_prompt(store.state))
        store.set_release_notes(release_notes)
        store.set_deploy_plan(deploy_plan)
        write_artifact(self.context, store.state.task_id, "release_notes.md", release_notes)
        write_artifact(self.context, store.state.task_id, "deploy_plan.md", deploy_plan)

    def _run_validation_commands(self) -> ValidationSummary:
        lint_result = run_lint(self.context)
        test_result = run_tests(self.context)
        return ValidationSummary(lint=lint_result, tests=test_result)

    def _update_validation_state(self, store: WorkflowStateStore, validation: ValidationSummary) -> None:
        store.state.lint_result = validation.lint
        store.state.test_result = validation.tests
        self.artifact_manager.write_json(
            store.state.task_id,
            "test_report.json",
            {
                "lint": _command_result_to_dict(validation.lint),
                "tests": _command_result_to_dict(validation.tests),
                "passed": validation.passed,
            },
        )

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
        errors = "\n".join(state.errors) or "none"
        return (
            f"Original request:\n{state.original_request}\n\n"
            f"Approved plan:\n{state.implementation_plan}\n\n"
            f"Known review findings:\n{findings}\n"
            f"Known errors:\n{errors}\n"
            "Make minimal safe changes and keep scope tight."
        )

    def _review_prompt(self, state: WorkflowState, diff_text: str) -> str:
        return (
            "Review repository changes as a strict reviewer. "
            "Focus on regressions, missing tests, edge cases, and maintainability.\n\n"
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

    def _safe_git_diff(self) -> str:
        from sdk_agent.tools.git_tools import git_diff

        result = git_diff(self.context)
        return result.stdout

    def _parse_review_text(self, text: str) -> list[ReviewFinding]:
        lowered = text.lower()
        severity = Severity.MEDIUM
        if "critical" in lowered:
            severity = Severity.CRITICAL
        elif "high" in lowered:
            severity = Severity.HIGH
        elif "low" in lowered:
            severity = Severity.LOW
        return [ReviewFinding(title="Review summary", details=text, severity=severity)]


def _command_result_to_dict(result: CommandResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "command": result.command,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
