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
        status_tracker=None,
        runner=None,
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
        self.status_tracker = status_tracker
        self.runner = runner

    async def _run_stage(
        self,
        agent_name: str,
        stage_key: str,
        prompt: str,
        progress_start: int,
        progress_end: int,
        agent,
    ):
        if self.status_tracker:
            self.status_tracker.update_agent(
                name=agent_name,
                stage=f"{stage_key}:running",
                progress=progress_start,
                message="started",
            )

        result = await self.runner.run(agent, prompt)

        if self.status_tracker:
            self.status_tracker.update_agent(
                name=agent_name,
                stage=f"{stage_key}:completed",
                progress=progress_end,
                message="done",
            )

        return result.final_output

    async def run(self, request: str) -> dict:
        if self.runner is None:
            from agents import Runner

            self.runner = Runner

        results = {
            "plan": None,
            "implementation": None,
            "test_report": None,
            "review_report": None,
            "deploy_report": None,
            "skipped_stages": [],
            "run_id": None,
        }

        if self.status_tracker:
            self.status_tracker.register_agents(["planner", "developer", "tester", "reviewer", "deployer"])
            run_record = self.status_tracker.start_run(request=request)
            results["run_id"] = run_record.run_id

        active_run_id = results["run_id"]

        try:
            planning_prompt = self.prompt_overrides.get(
                "planning",
                f"Create a clear implementation plan for this request:\n\n{request}",
            )

            if self.run_planning and self.planner:
                plan = await self._run_stage(
                    agent_name="planner",
                    stage_key="planning",
                    prompt=planning_prompt,
                    progress_start=5,
                    progress_end=20,
                    agent=self.planner,
                )
                results["plan"] = plan
            else:
                plan = request
                results["skipped_stages"].append("planning")
                if self.status_tracker:
                    self.status_tracker.update_agent("planner", "planning:skipped", 0, "skipped")

            implementation_prompt = self.prompt_overrides.get(
                "implementation",
                f"Implement the following approved plan:\n\n{plan}",
            )

            if self.developer:
                results["implementation"] = await self._run_stage(
                    agent_name="developer",
                    stage_key="implementation",
                    prompt=implementation_prompt,
                    progress_start=25,
                    progress_end=55,
                    agent=self.developer,
                )
            else:
                results["skipped_stages"].append("implementation")
                if self.status_tracker:
                    self.status_tracker.update_agent("developer", "implementation:skipped", 0, "skipped")

            testing_prompt = self.prompt_overrides.get(
                "testing",
                "Run validation checks, identify gaps, and report the testing status.",
            )

            if self.run_testing and self.tester:
                results["test_report"] = await self._run_stage(
                    agent_name="tester",
                    stage_key="testing",
                    prompt=testing_prompt,
                    progress_start=60,
                    progress_end=75,
                    agent=self.tester,
                )
            else:
                results["skipped_stages"].append("testing")
                if self.status_tracker:
                    self.status_tracker.update_agent("tester", "testing:skipped", 0, "skipped")

            review_prompt = self.prompt_overrides.get(
                "review",
                "Review the proposed changes and identify risks, bugs, or maintainability issues.",
            )

            if self.run_review and self.reviewer:
                results["review_report"] = await self._run_stage(
                    agent_name="reviewer",
                    stage_key="review",
                    prompt=review_prompt,
                    progress_start=80,
                    progress_end=90,
                    agent=self.reviewer,
                )
            else:
                results["skipped_stages"].append("review")
                if self.status_tracker:
                    self.status_tracker.update_agent("reviewer", "review:skipped", 0, "skipped")

            deploy_prompt = self.prompt_overrides.get(
                "deploy",
                "Prepare staging deployment steps, rollback plan, and post-deploy checks.",
            )

            if self.run_deploy and self.deployer:
                results["deploy_report"] = await self._run_stage(
                    agent_name="deployer",
                    stage_key="deploy",
                    prompt=deploy_prompt,
                    progress_start=92,
                    progress_end=100,
                    agent=self.deployer,
                )
            else:
                results["skipped_stages"].append("deploy")
                if self.status_tracker:
                    self.status_tracker.update_agent("deployer", "deploy:skipped", 0, "skipped")

            if self.status_tracker and active_run_id:
                self.status_tracker.finish_run(run_id=active_run_id, status="completed")

            return results
        except Exception:
            if self.status_tracker and active_run_id:
                self.status_tracker.finish_run(run_id=active_run_id, status="failed")
            raise
