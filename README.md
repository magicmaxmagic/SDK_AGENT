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

pip install -e .

## Requirements

- Python 3.10+
- Codex CLI installed and available in PATH
- Environment variable OPENAI_API_KEY set

Optional if using custom endpoint:

- OPENAI_BASE_URL

## Run from CLI

python -m sdk_agent.main "my task"

Optional arguments:

python -m sdk_agent.main "my task" --repo-path /home/user/myrepo --project-name myrepo --model gpt-5-codex

## What happens at runtime

- The process opens Codex MCP server via MCPServerStdio
- All role agents are connected to this MCP server
- The workflow runs:
  plan -> implement -> test -> review -> deploy prep
- The final output is printed as JSON

## Test

pip install -e .[dev]
pytest
