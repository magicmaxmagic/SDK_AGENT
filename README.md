# sdk_agent

sdk_agent is a policy-driven autonomous engineering control plane for software delivery workflows.

It combines deterministic platform controls with OpenAI Agents SDK and Codex MCP to support:
- planning and architecture reviews
- controlled implementation and validation
- structured review and security review
- release preparation and deployment planning
- resumable long-running runs with audit trails
- graph-based workflow introspection for visual runtime UIs

## Core Principles

- Safety first: controls are code-enforced.
- Zero trust by default: actions are policy-evaluated.
- Reproducible execution: state, logs, artifacts, and decisions are persisted.
- Staged autonomy: trust levels constrain what autonomy can do.

## Architecture

- `src/sdk_agent/core/`: workflow engine, runtime controls, policy engine, persistence, audit, sensitivity, git workflow, transitions.
- `src/sdk_agent/graph/`: typed workflow graph model, definitions, layout metadata, serializers, execution view projection.
- `src/sdk_agent/api/`: payload schemas/builders for graph and run inspection endpoints.
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
- `definition.json`
- `execution_history.json`
- `graph_view.json`
- `audit_log.jsonl`
- `plan.md`
- `changed_files.json`
- `lint_report.json`
- `test_report.json`
- `review_report.json`
- `security_review.json`
- `security_report.json`
- `release_notes.md`
- `deploy_plan.md`
- `rollback_plan.md`
- `health_check.sh`
- `evaluation_report.json`
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
- `inspect-graph --run-id <id>`
- `inspect-run --run-id <id>`
- `deploy-staging --run-id <id>`
- `deploy-production --run-id <id>`
- `approve-staging --run-id <id> --approved-by <user> --ticket <id> --ticket-source <src> --reason <text> [--expires-in-minutes <n>]`
- `approve-production --run-id <id> --approved-by <user> --ticket <id> --ticket-source <src> --reason <text> [--expires-in-minutes <n>]`
- `audit --run-id <id> [--flat-fields]`
- `audit-export-siem --run-id <id> [--flat-fields] [--batch-size <n>] [--max-file-size-bytes <n>]`
- `audit-verify-chain --run-id <id> [--skip-siem-exports] [--strict]`
- `audit-repair-chain --run-id <id> [--skip-siem-exports]`

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
- `--production-approval-validity-minutes`
- `--required-staging-approvals`
- `--required-production-approvals`
- `--ticket-connector`
- `--ticket-connector-settings`
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

Inspect workflow graph definition (for UI rendering):

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio inspect-graph --run-id run-abc123
~~~

Inspect run state + graph + execution history (for runtime dashboards):

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio inspect-run --run-id run-abc123
~~~

Prepare staging deployment for a run:

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio deploy-staging --run-id run-abc123
~~~

Add explicit human approval before staging deployment:

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio approve-staging --run-id run-abc123 --approved-by qa.lead --ticket INC-4242 --ticket-source itsm --reason "Staging gate"
~~~

Add explicit human approval before production deployment:

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio approve-production --run-id run-abc123 --approved-by oncall.lead --ticket CHG-4242 --ticket-source cab --reason "CAB approved"
~~~

Second approval for 4-eyes before production deployment:

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio approve-production --run-id run-abc123 --approved-by sre.lead --ticket CHG-4243 --ticket-source jira --reason "Second approval" --expires-in-minutes 60
~~~

Deploy to production after approval:

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio deploy-production --run-id run-abc123
~~~

Read audit trail:

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio audit --run-id run-abc123
~~~

Read audit trail with flat ECS-like fields (SIEM ingestion):

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio audit --run-id run-abc123 --flat-fields
~~~

Export dedicated SIEM NDJSON batches with file rotation:

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio audit-export-siem --run-id run-abc123 --flat-fields --batch-size 1000 --max-file-size-bytes 1048576
~~~

Verify forensics chain integrity:

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio audit-verify-chain --run-id run-abc123
~~~

Strict verification (fails if SIEM manifest is missing or incomplete):

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio audit-verify-chain --run-id run-abc123 --strict
~~~

Repair chain on an immutable forensic snapshot directory (never in-place):

~~~bash
uv run python -m sdk_agent.main --repo-path /home/maxence/Documents/portfolio audit-repair-chain --run-id run-abc123
~~~

Audit events are SIEM-compatible and versioned (`schema_version=siem.audit.v1`, `event_version=1`) with stable fields such as `event_type`, `run_id`, `correlation_id`, `actor_role`, `action`, and `siem.event.*` mappings.

Forensics reinforcement: audit events, ticket validation logs, and SIEM NDJSON exports are chain-signed (`sha256`) with `forensics.prev_hash`/`forensics.chain_hash`, and SIEM export writes `siem_export_manifest.json` with final chain hash.

Ticket validation now runs through an external connector (`mock`, `jira`, `servicenow`, or `composite`) configured by plugin/project policy. CLI can override via `--ticket-connector` and `--ticket-connector-settings`.

Connector HTTP resilience supports retry/backoff and circuit breaker controls through `--ticket-connector-settings` (for example: `retry_attempts`, `backoff_initial_seconds`, `backoff_multiplier`, `circuit_failure_threshold`, `circuit_reset_seconds`, `timeout_seconds`).

Circuit breaker state can be persisted cross-process with a local TTL file using connector setting `circuit_state_file` (or env var `SDK_AGENT_CIRCUIT_STATE_FILE`) so protection survives restarts.

Example Jira HTTP connector override:

~~~bash
export JIRA_USER_EMAIL="bot@example.com"
export JIRA_API_TOKEN="***"
uv run python -m sdk_agent.main \
	--repo-path /home/maxence/Documents/portfolio \
	--ticket-connector jira \
	--ticket-connector-settings '{"base_url":"https://jira.example.com","auth_mode":"basic","accepted_sources":["jira"]}' \
	approve-production --run-id run-abc123 --approved-by oncall.lead --ticket CHG-4242 --ticket-source jira --reason "CAB approved"
~~~

Example ServiceNow HTTP connector override:

~~~bash
export SERVICENOW_USER="agent"
export SERVICENOW_PASSWORD="***"
uv run python -m sdk_agent.main \
	--repo-path /home/maxence/Documents/portfolio \
	--ticket-connector servicenow \
	--ticket-connector-settings '{"base_url":"https://snow.example.com","auth_mode":"basic","accepted_sources":["itsm","cab"]}' \
	approve-staging --run-id run-abc123 --approved-by qa.lead --ticket INC-4242 --ticket-source itsm --reason "staging gate"
~~~

Approval quorum is project-policy driven per target: staging and production thresholds come from plugin defaults and can be overridden from CLI when needed. Approval validity defaults to 120 minutes.

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

## Frontend + Backend Authentifie (Vercel + Supabase)

Un frontend/backend web est disponible dans `apps/web` (Next.js App Router).

Fonctionnalites incluses:
- frontend public + page de connexion (`/login`)
- dashboard protege (`/dashboard`)
- route backend privee (`/api/private`) qui exige une session Supabase
- middleware de protection pour les routes privees

Bootstrap base SaaS multi-tenant (organizations/projects/memberships/subscriptions):
- Executer `apps/web/supabase/saas.sql` dans l'editeur SQL Supabase.
- Script notes simple disponible aussi: `apps/web/supabase/notes.sql`.

### Variables d'environnement

Copie `apps/web/.env.example` vers `apps/web/.env.local` puis configure:
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

### Lancer en local

~~~bash
cd apps/web
npm install
npm run dev
~~~

### Deployer sur Vercel

1. Importer le repo dans Vercel.
2. Configurer `apps/web` comme Root Directory du projet Vercel.
3. Ajouter les variables d'environnement Vercel:
	- `NEXT_PUBLIC_SUPABASE_URL`
	- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
4. Deploy.

Une fois deploye:
- `/login` gere l'auth utilisateur via Supabase
- `/dashboard` et `/api/private` sont accessibles uniquement avec session valide

## Automatisation CI/CD + GitHub Copilot

Le repo inclut un workflow GitHub Actions unique:
- `.github/workflows/ci-cd.yml`

Ce pipeline execute automatiquement:
- tests Python (`uv sync --extra dev` puis `uv run pytest -q`)
- qualite Web (`npm ci`, `npm run lint`, `npm run build` dans `apps/web`)
- deploiement preview Vercel sur pull requests (URL automatique dans le Job Summary)
- deploiement production Vercel sur push `main` si les checks passent

Secrets GitHub a configurer pour le deploy Vercel:
- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

Durcissement recommande (GitHub Settings):
1. Branch protection sur `main`: activer `Require a pull request before merging`.
2. Branch protection sur `main`: activer `Require status checks to pass before merging`.
3. Branch protection sur `main`: ajouter `Python Tests` et `Web Lint and Build` comme required checks.
4. Environment `production`: ajouter des `Required reviewers` (release managers / owners).
5. Environment `production`: le job `Deploy to Vercel (Production)` attendra l'approbation avant de deployer.
6. Environment `preview`: optionnel pour isoler les secrets preview.
7. Environment `preview`: le job preview est ignore pour PR fork ou si secrets absents.

Configuration Copilot partagee:
- `.github/copilot-instructions.md`

Pour activer l'automatisation Copilot sur pull requests:
1. Ouvrir GitHub repository settings.
2. Activer GitHub Copilot code review pour le repository.
3. Utiliser ces instructions repo pour guider les suggestions et corrections automatiques.

## Current Limits

- Production deployment remains policy-disabled by default for safety.
- Worktree/container execution hooks are extensible but not full container orchestration yet.
- Security review parser is structured but heuristic in current version.
- Visual editor/front-end is intentionally decoupled; this repo currently provides the control-plane backend and inspectable artifacts/APIs.

## Safe Path to Higher Autonomy

1. Start with `suggest` or `implement` on low-risk repositories.
2. Validate audit and artifact quality.
3. Enable staging deploy only after stable validation/review quality.
4. Keep production deploy denied unless explicit trust profile and policy approval are in place.
