from sdk_agent.context import ProjectContext
from sdk_agent.config import TeamConfig
from sdk_agent.core.base_agent import BaseAgentFactory
from sdk_agent.core.workflow import SoftwareDeliveryWorkflow
from sdk_agent.plugins.base import BaseProjectPlugin
from sdk_agent.roles.planner import make_planner_agent
from sdk_agent.roles.developer import make_developer_agent
from sdk_agent.roles.tester import make_tester_agent
from sdk_agent.roles.reviewer import make_reviewer_agent
from sdk_agent.roles.deployer import make_deployer_agent


ROLE_NAMES = ("planner", "developer", "tester", "reviewer", "deployer")


def _merge_role_tools(
    role_name: str,
    explicit_tools: list | None,
    team_config: TeamConfig,
    plugins: list[BaseProjectPlugin],
) -> list:
    merged_tools = []

    merged_tools.extend(team_config.shared_tools)

    for plugin in plugins:
        merged_tools.extend(plugin.get_shared_tools())

    for plugin in plugins:
        merged_tools.extend(plugin.get_role_tools().get(role_name, []))

    if explicit_tools:
        merged_tools.extend(explicit_tools)

    role_config = team_config.role(role_name)
    if role_config.tools:
        merged_tools.extend(role_config.tools)

    return merged_tools


def _merge_instruction_suffix(
    role_name: str,
    context: ProjectContext,
    team_config: TeamConfig,
    plugins: list[BaseProjectPlugin],
) -> str | None:
    parts = []

    for plugin in plugins:
        suffix = plugin.get_role_instruction_suffixes().get(role_name)
        if suffix:
            parts.append(suffix)

    role_suffix = team_config.role(role_name).instructions_suffix
    if role_suffix:
        parts.append(role_suffix)

    if context.notes:
        parts.append("Project notes:\n- " + "\n- ".join(context.notes))

    if not parts:
        return None

    return "\n\n".join(parts)


def _merge_workflow_prompts(
    team_config: TeamConfig,
    plugins: list[BaseProjectPlugin],
) -> dict[str, str]:
    prompts = {}

    for plugin in plugins:
        prompts.update(plugin.get_workflow_prompt_overrides())

    prompts.update(team_config.workflow.prompt_overrides)
    return prompts


def build_software_team(
    context: ProjectContext,
    model: str | None = None,
    developer_tools: list | None = None,
    tester_tools: list | None = None,
    reviewer_tools: list | None = None,
    deployer_tools: list | None = None,
    team_config: TeamConfig | None = None,
    plugins: list[BaseProjectPlugin] | None = None,
    status_tracker=None,
) -> dict:
    team_config = team_config or TeamConfig()
    plugins = plugins or []

    effective_model = model or team_config.model
    factory = BaseAgentFactory(model=effective_model)

    role_configs = {role_name: team_config.role(role_name) for role_name in ROLE_NAMES}

    planner = None
    if role_configs["planner"].enabled:
        planner = make_planner_agent(
            factory,
            context,
            instructions_override=role_configs["planner"].instructions_override,
            instructions_suffix=_merge_instruction_suffix("planner", context, team_config, plugins),
        )

    developer = None
    if role_configs["developer"].enabled:
        developer = make_developer_agent(
            factory,
            context,
            tools=_merge_role_tools("developer", developer_tools, team_config, plugins),
            instructions_override=role_configs["developer"].instructions_override,
            instructions_suffix=_merge_instruction_suffix("developer", context, team_config, plugins),
        )

    tester = None
    if role_configs["tester"].enabled:
        tester = make_tester_agent(
            factory,
            context,
            tools=_merge_role_tools("tester", tester_tools, team_config, plugins),
            instructions_override=role_configs["tester"].instructions_override,
            instructions_suffix=_merge_instruction_suffix("tester", context, team_config, plugins),
        )

    reviewer = None
    if role_configs["reviewer"].enabled:
        reviewer = make_reviewer_agent(
            factory,
            context,
            tools=_merge_role_tools("reviewer", reviewer_tools, team_config, plugins),
            instructions_override=role_configs["reviewer"].instructions_override,
            instructions_suffix=_merge_instruction_suffix("reviewer", context, team_config, plugins),
        )

    deployer = None
    if role_configs["deployer"].enabled:
        deployer = make_deployer_agent(
            factory,
            context,
            tools=_merge_role_tools("deployer", deployer_tools, team_config, plugins),
            instructions_override=role_configs["deployer"].instructions_override,
            instructions_suffix=_merge_instruction_suffix("deployer", context, team_config, plugins),
        )

    workflow_prompts = _merge_workflow_prompts(team_config, plugins)

    workflow = SoftwareDeliveryWorkflow(
        planner=planner,
        developer=developer,
        tester=tester,
        reviewer=reviewer,
        deployer=deployer,
        run_planning=team_config.workflow.run_planning,
        run_testing=team_config.workflow.run_testing,
        run_review=team_config.workflow.run_review,
        run_deploy=team_config.workflow.run_deploy,
        prompt_overrides=workflow_prompts,
        status_tracker=status_tracker,
    )

    return {
        "planner": planner,
        "developer": developer,
        "tester": tester,
        "reviewer": reviewer,
        "deployer": deployer,
        "workflow": workflow,
    }
