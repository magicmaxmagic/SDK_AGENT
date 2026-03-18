# SDK_AGENT

Reusable Python package to build multi-agent software engineering workflows with the OpenAI Agents SDK.

## Features

- Reusable agent factories
- Standard software roles:
  - Planner
  - Developer
  - Tester
  - Reviewer
  - Deployer
- Shared project context
- Reusable workflow orchestration
- Plugin-ready architecture for multiple projects
- Fully customizable team configuration (roles, prompts, workflow stages, tools)
- Codex/shell/MCP tool injection via plugins

## Installation

### Local editable install

```bash
pip install -e .
```

### Install from GitHub

```bash
pip install "sdk-agent @ git+https://github.com/magicmaxmagic/SDK_AGENT.git@main"
```

## Example

```python
from sdk_agent import build_software_team
from sdk_agent.context import ProjectContext

context = ProjectContext(
    project_name="portfolio",
    repo_path="/home/maxence/Documents/portfolio",
    test_command="npm test",
    lint_command="npm run lint",
)

team = build_software_team(context=context)
print(team.keys())
```

## Advanced Customization (Multi-Project)

```python
from sdk_agent import (
  ProjectContext,
  TeamConfig,
  RoleConfig,
  WorkflowConfig,
  build_software_team,
)
from sdk_agent.plugins.base import BaseProjectPlugin


class PortfolioPlugin(BaseProjectPlugin):
  def get_shared_tools(self) -> list:
    return ["shell", "filesystem"]

  def get_role_tools(self) -> dict[str, list]:
    return {
      "developer": ["codex"],
      "tester": ["shell"],
      "deployer": ["shell"],
    }

  def get_role_instruction_suffixes(self) -> dict[str, str]:
    return {
      "developer": "Respect existing React architecture and keep patches minimal.",
      "tester": "Always run unit tests first, then lint checks.",
    }


context = ProjectContext(
  project_name="portfolio",
  repo_path="/home/maxence/Documents/portfolio",
  test_command="npm test",
  lint_command="npm run lint",
  notes=["Do not break current UI routes", "Prefer incremental changes"],
)

config = TeamConfig(
  model="gpt-5-codex",
  shared_tools=["repo_search"],
  roles={
    "reviewer": RoleConfig(enabled=True),
    "deployer": RoleConfig(enabled=False),
    "developer": RoleConfig(
      instructions_suffix="Always provide a rollback-safe implementation path.",
    ),
  },
  workflow=WorkflowConfig(
    run_planning=True,
    run_testing=True,
    run_review=True,
    run_deploy=False,
    prompt_overrides={
      "testing": "Execute tests, report failures, propose minimal fixes.",
    },
  ),
)

team = build_software_team(
  context=context,
  team_config=config,
  plugins=[PortfolioPlugin(context=context)],
)

print(team["workflow"])
```

## What Is Customizable

- Activate or disable roles (`planner`, `developer`, `tester`, `reviewer`, `deployer`)
- Override role instructions entirely, or append project constraints
- Inject shared tools for all roles or role-specific tools only
- Enable/disable workflow stages (planning, testing, review, deploy)
- Override workflow prompts per stage
- Attach project plugins to adapt behavior per repository/domain
