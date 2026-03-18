from __future__ import annotations


class SoftwareDeliveryWorkflow:
    def __init__(self, planner, developer, tester, reviewer, deployer):
        self.planner = planner
        self.developer = developer
        self.tester = tester
        self.reviewer = reviewer
        self.deployer = deployer

    async def run(self, request: str) -> dict:
        from agents import Runner

        plan_result = await Runner.run(
            self.planner,
            f"Create a concise implementation plan for this request:\n\n{request}",
        )
        plan = plan_result.final_output

        implementation_result = await Runner.run(
            self.developer,
            f"Implement the approved plan with the smallest safe diff:\n\n{plan}",
        )

        test_result = await Runner.run(
            self.tester,
            "Run validation checks, identify gaps, and report the testing status.",
        )

        review_result = await Runner.run(
            self.reviewer,
            "Review changes for bugs, regressions, edge cases, maintainability issues, and missing tests.",
        )

        deploy_result = await Runner.run(
            self.deployer,
            (
                "Prepare deployment only for staging. "
                "Return rollout steps, rollback plan, and post-deploy checks. "
                "Never auto deploy to production."
            ),
        )

        return {
            "plan": plan,
            "implementation": implementation_result.final_output,
            "test_report": test_result.final_output,
            "review_report": review_result.final_output,
            "deploy_prep": deploy_result.final_output,
        }
