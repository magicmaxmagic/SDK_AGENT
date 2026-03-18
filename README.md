# sdk_agent

sdk_agent is a policy-driven autonomous engineering platform for software delivery workflows.

It combines deterministic platform controls with OpenAI Agents SDK and Codex MCP to support:
- planning and architecture reviews
- controlled implementation and validation
- structured review and security review
- release preparation and deployment planning
- resumable long-running runs with audit trails

## Core Principles

- Safety first: controls are code-enforced.
- Zero trust by default: actions are policy-evaluated.
- Reproducible execution: state, logs, artifacts, and decisions are persisted.
- Staged autonomy: trust levels constrain what autonomy can do.

## Architecture

- `src/sdk_agent/core/`: workflow engine, policy engine, persistence, audit, sensitivity, git workflow, transitions.
- `src/sdk_agent/roles/`: triage, planner, architect, developer, tester, reviewer, security reviewer, release manager, deployer, policy enforcer.
- `src/sdk_agent/tools/`: deterministic shell/git/file/validation/artifact/policy/persistence tooling.
- `src/sdk_agent/plugins/`: project-specific trust profile, commands, rules, and restrictions.
- `src/sdk_agent/cli.py`: operational CLI commands.

## Autonomy Levels

Supported typed autonomy levels:
- `observe`
- `suggest`
- `implement`
- `validate`
- `staging_deploy`
- `production_candidate`
- `fully_autonomous`

Higher levels are gated by trust profile policy.

## Trust Profiles

- `low_risk_sandbox`
- `normal_internal`
- `sensitive`
- `critical`

Trust profiles define max autonomy, write/commit/pr permissions, deploy permissions, and human approval requirements.

## Policy Engine

Central policy checks evaluate each critical action against:
- role
- autonomy level
- trust profile
- environment
- action type
- target branch/path

Examples of gated actions:
- file edits
- branch/worktree creation
- shell execution
- deploy staging/production
- commit and PR draft preparation
- protected path modifications

## Execution Isolation

The platform supports isolation through:
- run-specific branch creation
- optional git worktree creation per run
- per-run artifact directory

No automated push is performed.

## Resumable Runs

Every run persists state in:
- `.sdk_agent_runs/<run_id>/state.json`

Commands support resume/status/audit and deploy actions based on run id.

## Artifacts and Audit

Per run outputs under `.sdk_agent_runs/<run_id>/` include:
- `state.json`
- `audit_log.jsonl`
- `plan.md`
- `changed_files.json`
- `lint_report.json`
- `test_report.json`
- `review_report.json`
- `security_review.json`
- `release_notes.md`
- `deploy_plan.md`
- `rollback_plan.md`
- `final_summary.json`

## CLI Commands

Main operational commands:
- `feature`
- `bugfix`
- `plan`
- `validate`
- `review`
- `resume --run-id <id>`
- `status --run-id <id>`
- `deploy-staging --run-id <id>`
- `deploy-production --run-id <id>`
- `approve-production --run-id <id> --approved-by <user> --ticket <id> --reason <text>`
- `audit --run-id <id>`

Key options:
- `--repo-path`
- `--project-name`
- `--plugin`
- `--model`
- `--artifacts-dir`
- `--autonomy-level`
- `--trust-profile`
- `--branch-name`
- `--use-worktree`
- `--allow-commit`
- `--allow-pr-draft`
- `--allow-staging-deploy`
- `--allow-production-deploy`
- `--dry-run`

## Usage Examples (uv)

Run feature flow:

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio --plugin nextjs --autonomy-level implement feature "Add team management page"
~~~

Run validate flow:

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio --plugin nextjs validate
~~~

Resume a run:

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio resume --run-id run-abc123
~~~

Check status:

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio status --run-id run-abc123
~~~

Prepare staging deployment for a run:

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio deploy-staging --run-id run-abc123
~~~

Add explicit human approval before production deployment:

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio approve-production --run-id run-abc123 --approved-by oncall.lead --ticket CHG-4242 --reason "CAB approved"
~~~

Deploy to production after approval:

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio deploy-production --run-id run-abc123
~~~

Read audit trail:

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio audit --run-id run-abc123
~~~

Audit events are SIEM-compatible and versioned (`schema_version=siem.audit.v1`, `event_version=1`) with stable fields such as `event_type`, `run_id`, `correlation_id`, `actor_role`, `action`, and `siem.event.*` mappings.

Dry-run simulation:

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio --dry-run feature "Refactor auth middleware"
~~~

## Installation

Local development:

~~~bash
uv sync --extra dev
uv run pytest -q
~~~

Install from GitHub:

~~~bash
pip install "git+https://github.com/magicmaxmagic/SDK_AGENT.git"
~~~

Or with uv:

~~~bash
uv add "git+https://github.com/magicmaxmagic/SDK_AGENT.git"
~~~

## Current Limits

- Production deployment remains policy-disabled by default for safety.
- Worktree/container execution hooks are extensible but not full container orchestration yet.
- Security review parser is structured but heuristic in current version.

## Safe Path to Higher Autonomy

1. Start with `suggest` or `implement` on low-risk repositories.
2. Validate audit and artifact quality.
3. Enable staging deploy only after stable validation/review quality.
4. Keep production deploy denied unless explicit trust profile and policy approval are in place.
