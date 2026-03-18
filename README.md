# sdk_agent

A reusable Python package that orchestrates a software-delivery team with OpenAI Agents SDK.

It uses Codex CLI as an MCP server through MCPServerStdio with:
- command: codex
- args: ["mcp-server"]

## Features

- Reusable ProjectContext dataclass
- Reusable Agent factory
- Multi-step workflow:
  1) Plan
  2) Implement
  3) Test
  4) Review
  5) Deploy preparation
- Production safety:
  - Never auto deploy to production
  - Deployer only returns deployment checklist and rollback plan

## Install

1. Create and activate a virtual environment
2. Install package

Example:

uv sync

## Requirements

- Python 3.10+
- Codex CLI installed and available in PATH
- Environment variable OPENAI_API_KEY set

Optional if using custom endpoint:

- OPENAI_BASE_URL

## Run from CLI

uv run python -m sdk_agent.main "my task"

Optional arguments:

uv run python -m sdk_agent.main "my task" --repo-path /home/user/myrepo --project-name myrepo --model gpt-5-codex

## Lancer les agents (guide rapide)

### 1) Depuis le repo SDK

cd /home/maxence/Documents/SDK_AGENT
uv sync
export OPENAI_API_KEY="YOUR_KEY"
uv run python -m sdk_agent.main "Ameliore le portfolio avec un plan, implementation, tests, review, et preparation de deploiement"

### 2) Cibler explicitement ton repo portfolio

cd /home/maxence/Documents/SDK_AGENT
uv sync
export OPENAI_API_KEY="YOUR_KEY"
uv run python -m sdk_agent.main "Ameliore tout mon portfolio pour qu'il soit tres professionnel" \
  --project-name portfolio \
  --repo-path /home/maxence/Documents/portfolio \
  --test-command "npm test" \
  --lint-command "npm run lint" \
  --model gpt-5-codex

### 3) Utiliser le script console (equivalent)

cd /home/maxence/Documents/SDK_AGENT
uv sync
export OPENAI_API_KEY="YOUR_KEY"
uv run sdk-agent "Ajoute une nouvelle section Projects avec validation complete" \
  --project-name portfolio \
  --repo-path /home/maxence/Documents/portfolio

### 3bis) Sans cle API (Codex local), depuis n'importe quel dossier

uv run --project /home/maxence/Documents/SDK_AGENT python -m sdk_agent.cli.run_portfolio "Ajoute une nouvelle section Projects avec validation complete" \
  --executor codex-cli \
  --project-name portfolio \
  --repo-path /home/maxence/Documents/portfolio

Option (desactivee par defaut): commit/push automatique apres succes

uv run --project /home/maxence/Documents/SDK_AGENT python -m sdk_agent.cli.run_portfolio "Ajoute une nouvelle section Projects avec validation complete" \
  --executor codex-cli \
  --project-name portfolio \
  --repo-path /home/maxence/Documents/portfolio \
  --auto-commit \
  --commit-message "feat: add projects section via sdk-agent" \
  --auto-push \
  --push-remote origin \
  --push-branch main

### 4) Avec endpoint compatible OpenAI (optionnel)

cd /home/maxence/Documents/SDK_AGENT
uv sync
export OPENAI_API_KEY="YOUR_KEY"
export OPENAI_BASE_URL="http://127.0.0.1:11434/v1"
uv run python -m sdk_agent.main "Refactor home page en gardant les routes existantes" \
  --project-name portfolio \
  --repo-path /home/maxence/Documents/portfolio \
  --model qwen3:8b

## What happens at runtime

- The process opens Codex MCP server via MCPServerStdio
- All role agents are connected to this MCP server
- The workflow runs:
  plan -> implement -> test -> review -> deploy prep
- The final output is printed as JSON

## Test

uv sync --extra dev
uv run pytest
