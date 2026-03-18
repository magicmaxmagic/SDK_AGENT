# Changelog

## v1.1.0 - production-grade foundation

Date: 2026-03-18

### Added
- Strict CLI operational flags:
  - `--branch-name`
  - `--allow-commit`
  - `--allow-staging-deploy`
  - `--enable-tester-mcp`
  - `--dry-run`
- Dedicated git workflow module: `src/sdk_agent/core/git_workflow.py`
- Structured reviewer findings parsing with normalized schema in `src/sdk_agent/roles/reviewer.py`.
- Extended git tooling:
  - `git_current_branch`
  - `git_collect_changed_files`
  - `git_prepare_commit_message`
  - `git_prepare_pr_body`
- New tests:
  - `tests/test_cli.py`
  - `tests/test_git_tools.py`
  - `tests/test_review_parsing.py`
  - `tests/test_workflow_engine_feature_flow.py`
  - `tests/test_workflow_engine_retry_loop.py`

### Changed
- Workflow engine upgraded with explicit branching and retry-loop audit behavior.
- Workflow state enriched for auditability:
  - workflow kind, branch, histories, fix iteration metadata, final decision fields.
- Guardrails hardened with role-aware command blocking and stricter forbidden command patterns.
- Shell execution now supports dry-run simulation while preserving command validation.
- Plugin command allowlists expanded for branch and diff operations.
- README updated with advanced CLI usage, structured artifacts, and strengthened guardrails.

### Security And Safety
- `git push` is blocked from automated workflow execution.
- Destructive git and shell commands remain blocked by default guardrails.
- Production deployment remains disabled by default.

### Migration Notes
- Consumers should use `workflow_kind` (replacing `flow`) in serialized workflow state payloads.
- For dry simulation in CI or local checks, use `--dry-run`.
