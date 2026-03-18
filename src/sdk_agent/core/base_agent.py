class BaseAgentFactory:
    def __init__(self, model: str | None = None):
        self.model = model

    def create(
        self,
        name: str,
        instructions: str,
        tools: list | None = None,
        handoffs: list | None = None,
    ):
        from agents import Agent

        kwargs = {
            "name": name,
            "instructions": instructions,
        }

        if self.model:
            kwargs["model"] = self.model
        if tools:
            kwargs["tools"] = tools
        if handoffs:
            kwargs["handoffs"] = handoffs

        return Agent(**kwargs)
