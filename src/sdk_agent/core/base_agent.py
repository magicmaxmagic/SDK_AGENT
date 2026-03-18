from __future__ import annotations

class BaseAgentFactory:
    def __init__(self, model: str | None = None):
        self.model = model

    def create(
        self,
        name: str,
        instructions: str,
        mcp_servers: list | None = None,
        tools: list | None = None,
        handoffs: list | None = None,
    ):
        from agents import Agent

        kwargs: dict = {
            "name": name,
            "instructions": instructions,
        }

        if self.model:
            kwargs["model"] = self.model
        if mcp_servers:
            kwargs["mcp_servers"] = mcp_servers
        if tools:
            kwargs["tools"] = tools
        if handoffs:
            kwargs["handoffs"] = handoffs

        return Agent(**kwargs)
