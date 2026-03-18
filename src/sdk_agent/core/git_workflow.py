from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sdk_agent.context import ProjectContext
from sdk_agent.tools.git_tools import (
    git_collect_changed_files,
    git_create_branch,
    git_create_worktree,
    git_current_branch,
    git_diff,
    git_prepare_commit_message,
    git_prepare_pr_body,
)


@dataclass(slots=True)
class GitWorkflowPlan:
    branch_name: str
    worktree_path: str | None
    changed_files: list[str]
    commit_message: str
    pr_body: str
    diff_summary: str


def prepare_git_workflow(
    context: ProjectContext,
    request: str,
    branch_name: str | None,
    create_branch: bool,
    validation_summary: str,
    use_worktree: bool,
    run_id: str,
) -> GitWorkflowPlan:
    if create_branch and branch_name:
        git_create_branch(context, branch_name)

    current_branch = git_current_branch(context).stdout.strip()
    resolved_branch = branch_name or current_branch

    worktree_path: str | None = None
    if use_worktree:
        worktree_dir = context.resolved_artifact_root() / run_id / "worktree"
        git_create_worktree(context, resolved_branch, worktree_dir)
        worktree_path = str(worktree_dir)

    changed_files = git_collect_changed_files(context)
    commit_message = git_prepare_commit_message(request=request, changed_files=changed_files)
    pr_body = git_prepare_pr_body(
        request=request,
        changed_files=changed_files,
        validation_summary=validation_summary,
    )
    diff_summary = git_diff(context).stdout[:16000]

    return GitWorkflowPlan(
        branch_name=resolved_branch,
        worktree_path=worktree_path,
        changed_files=changed_files,
        commit_message=commit_message,
        pr_body=pr_body,
        diff_summary=diff_summary,
    )
