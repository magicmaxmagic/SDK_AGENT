# sdk_agent

Reusable software engineering agent platform for planning, implementation, validation, review, release preparation, and staging deployment planning.

The package is designed to be installed once and reused across multiple repositories.

## What It Does

- Runs role-specialized software agents with shared workflow state.
- Uses deterministic Python tools for shell, git, files, validation, and artifacts.
- Integrates Codex CLI through MCP stdio for coding assistance.
- Applies practical guardrails by default.
- Produces per-run artifacts under `.sdk_agent_runs/<task_id>/`.

## Architecture Overview

The package is split into layers:

1. Core platform layer
- workflow engine with conditional transitions
- workflow state model
- artifact manager
- transition helpers
- agent factory

2. Role layer
- Planner
- Developer
- Tester
- Reviewer
- ReleaseManager
- Deployer
- Triage

3. Tool layer
- safe file listing/reading
- guarded shell execution
- git status/diff/branch/changed files
- lint/test command wrappers
- artifact writing helpers

4. Plugin layer
- GenericProjectPlugin
- NextJsPlugin
- PythonAppPlugin

5. CLI layer
- `feature`
- `bugfix`
- `plan`
- `validate`
- `review`

## Repository Structure

- src/sdk_agent
- src/sdk_agent/core
- src/sdk_agent/roles
- src/sdk_agent/tools
- src/sdk_agent/plugins
- tests

## Install Locally

Requirements:
- Python 3.11+
- Codex CLI installed and authenticated

Using uv:

~~~bash
cd /home/maxence/Documents/SDK_AGENT
uv sync --extra dev
~~~

## Install From GitHub

~~~bash
pip install "git+https://github.com/magicmaxmagic/SDK_AGENT.git"
~~~

Or with uv in another repository:

~~~bash
uv add "git+https://github.com/magicmaxmagic/SDK_AGENT.git"
~~~

## Codex Authentication

Install Codex CLI and authenticate in your shell environment.

Typical local check:

~~~bash
codex --help
codex mcp-server --help
~~~

If you use OpenAI Agents SDK with OpenAI endpoint:

~~~bash
export OPENAI_API_KEY="YOUR_KEY"
~~~

## CLI Usage

Main entrypoint:

~~~bash
uv run python -m sdk_agent.main <command> [options]
~~~

Commands:
- feature <request>
- bugfix <request>
- plan <request>
- validate
- review

Common options:
- `--repo-path`
- `--project-name`
- `--plugin` (`generic`, `nextjs`, `python`)
- `--model`
- `--artifacts-dir`
- `--max-fix-iterations`
- `--branch-name`
- `--allow-commit`
- `--allow-staging-deploy`
- `--enable-tester-mcp`
- `--dry-run`

## Example Commands

Feature flow on Next.js repo:

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio --project-name portfolio --plugin nextjs --model gpt-5-codex feature "Add newsletter signup form"
~~~

Bugfix flow on Python repo:

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/api --project-name api --plugin python bugfix "Fix login redirect bug"
~~~

Validation-only flow:

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio --plugin nextjs validate
~~~

Review-only flow:

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio --plugin nextjs review
~~~

Plan-only flow:

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio --plugin nextjs plan "Build admin dashboard"
~~~

Feature flow with git branch draft and optional commit preparation:

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio --plugin nextjs --branch-name feature/signup --allow-commit feature "Add signup form"
~~~

Dry-run full simulation (no shell commands executed):

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio --plugin nextjs --dry-run feature "Add signup form"
~~~

## Role Responsibilities

Planner:
- creates implementation plan
- defines acceptance criteria and risks
- does not implement code

Developer:
- performs implementation with Codex MCP support
- keeps changes minimal and scoped
- does not deploy

Tester:
- runs lint and tests via deterministic commands
- reports failures for fix/retest loop

Reviewer:
- inspects diffs and changed files
- reports structured findings (`title`, `severity`, `file_path`, `recommendation`, `blocking`)
- read-only reviewer behavior

ReleaseManager:
- creates release notes
- builds validation and rollback summary

Deployer:
- generates staging deployment plan only
- never auto deploys production

Triage:
- classifies request flow
- supports orchestration decisions

## Plugins

Each plugin encapsulates project-specific behavior:

- repo path
- allowed shell command prefixes
- lint command
- test command
- optional build command
- staging deploy command
- project rules
- artifact root path

Built-in plugins:
- GenericProjectPlugin: mixed repositories
- NextJsPlugin: Node/Next.js conventions
- PythonAppPlugin: Python service conventions

## Artifacts

Every run writes outputs under:

- `.sdk_agent_runs/<task_id>/plan.md`
- `.sdk_agent_runs/<task_id>/changed_files.json`
- `.sdk_agent_runs/<task_id>/lint_report.json`
- `.sdk_agent_runs/<task_id>/test_report.json`
- `.sdk_agent_runs/<task_id>/review_report.json`
- `.sdk_agent_runs/<task_id>/release_notes.md`
- `.sdk_agent_runs/<task_id>/deploy_plan.md`
- `.sdk_agent_runs/<task_id>/commit_message.txt`
- `.sdk_agent_runs/<task_id>/pr_draft.md`
- `.sdk_agent_runs/<task_id>/final_summary.json`

## Guardrails

Enforced defaults include:
- repository sandbox path checks
- shell command allowlist per plugin
- rejection of destructive commands
- role-aware command restrictions
- no automatic production deploy
- no git push from workflow
- artifact path sandboxing

## Local Development and Tests

~~~bash
cd /home/maxence/Documents/SDK_AGENT
uv sync --extra dev
uv run pytest -q
~~~

## Current Limitations

- Reviewer finding parsing is text-based and intentionally simple in V1.
- Workflow currently loops with bounded retries instead of adaptive dynamic planning.
- MCP tool access is focused on Developer and Tester flows.

## Future Improvements

- Structured finding schema extraction from reviewer output.
- Richer branch policies and optional PR creation integration.
- Built-in metrics exporters and trace backends.
- Additional plugins for FastAPI, Django, and Streamlit templates.
