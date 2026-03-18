from __future__ import annotations

from dataclasses import dataclass

from sdk_agent.context import ProjectContext
from sdk_agent.tools.git_tools import (
    git_collect_changed_files,
    git_create_branch,
    git_current_branch,
    git_prepare_commit_message,
    git_prepare_pr_body,
)


@dataclass(slots=True)
class GitWorkflowPlan:
    branch_name: str
    changed_files: list[str]
    commit_message: str
    pr_body: str


def prepare_git_workflow(
    context: ProjectContext,
    request: str,
    branch_name: str | None,
    create_branch: bool,
    validation_summary: str,
) -> GitWorkflowPlan:
    if create_branch and branch_name:
        git_create_branch(context, branch_name)

    current_branch = git_current_branch(context).stdout.strip()
    resolved_branch = branch_name or current_branch
    changed_files = git_collect_changed_files(context)
    commit_message = git_prepare_commit_message(request=request, changed_files=changed_files)
    pr_body = git_prepare_pr_body(
        request=request,
        changed_files=changed_files,
        validation_summary=validation_summary,
    )
    return GitWorkflowPlan(
        branch_name=resolved_branch,
        changed_files=changed_files,
        commit_message=commit_message,
        pr_body=pr_body,
    )
