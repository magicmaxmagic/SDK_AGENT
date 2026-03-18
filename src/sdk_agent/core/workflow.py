class SoftwareDeliveryWorkflow:
    def __init__(
        self,
        planner,
        developer,
        tester,
        reviewer,
        deployer,
        run_planning: bool = True,
        run_testing: bool = True,
        run_review: bool = True,
        run_deploy: bool = True,
        prompt_overrides: dict[str, str] | None = None,
    ):
        self.planner = planner
        self.developer = developer
        self.tester = tester
        self.reviewer = reviewer
        self.deployer = deployer
        self.run_planning = run_planning
        self.run_testing = run_testing
        self.run_review = run_review
        self.run_deploy = run_deploy
        self.prompt_overrides = prompt_overrides or {}

    async def run(self, request: str) -> dict:
        from agents import Runner

        results = {
            "plan": None,
            "implementation": None,
            "test_report": None,
            "review_report": None,
            "deploy_report": None,
            "skipped_stages": [],
        }

        planning_prompt = self.prompt_overrides.get(
            "planning",
            f"Create a clear implementation plan for this request:\n\n{request}",
        )

        if self.run_planning and self.planner:
            plan_result = await Runner.run(self.planner, planning_prompt)
            plan = plan_result.final_output
            results["plan"] = plan
        else:
            plan = request
            results["skipped_stages"].append("planning")

        implementation_prompt = self.prompt_overrides.get(
            "implementation",
            f"Implement the following approved plan:\n\n{plan}",
        )

        if self.developer:
            implementation_result = await Runner.run(self.developer, implementation_prompt)
            results["implementation"] = implementation_result.final_output
        else:
            results["skipped_stages"].append("implementation")

        testing_prompt = self.prompt_overrides.get(
            "testing",
            "Run validation checks, identify gaps, and report the testing status.",
        )

        if self.run_testing and self.tester:
            test_result = await Runner.run(self.tester, testing_prompt)
            results["test_report"] = test_result.final_output
        else:
            results["skipped_stages"].append("testing")

        review_prompt = self.prompt_overrides.get(
            "review",
            "Review the proposed changes and identify risks, bugs, or maintainability issues.",
        )

        if self.run_review and self.reviewer:
            review_result = await Runner.run(self.reviewer, review_prompt)
            results["review_report"] = review_result.final_output
        else:
            results["skipped_stages"].append("review")

        deploy_prompt = self.prompt_overrides.get(
            "deploy",
            "Prepare staging deployment steps, rollback plan, and post-deploy checks.",
        )

        if self.run_deploy and self.deployer:
            deploy_result = await Runner.run(self.deployer, deploy_prompt)
            results["deploy_report"] = deploy_result.final_output
        else:
            results["skipped_stages"].append("deploy")

        return results
