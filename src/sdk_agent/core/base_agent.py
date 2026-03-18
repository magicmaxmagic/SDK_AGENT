from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class BaseAgentFactory:
    """Factory for OpenAI Agents with explicit role-scoped capabilities."""

    model: str

    def create(
        self,
        name: str,
        instructions: str,
        mcp_servers: list[Any] | None = None,
        tools: list[Any] | None = None,
    ) -> Any:
        from agents import Agent

        kwargs: dict[str, Any] = {
            "name": name,
            "instructions": instructions,
            "model": self.model,
        }
        if mcp_servers:
            kwargs["mcp_servers"] = mcp_servers
        if tools:
            kwargs["tools"] = tools

        return Agent(**kwargs)
