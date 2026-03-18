from __future__ import annotations

from contextlib import asynccontextmanager

from typing import AsyncIterator

from sdk_agent.logging_config import get_logger

LOGGER = get_logger("mcp")


def _load_mcp_stdio_class():
    try:
        from agents.mcp import MCPServerStdio

        return MCPServerStdio
    except Exception as exc:  # pragma: no cover - dependency absence is environment-specific
        raise RuntimeError(
            "OpenAI Agents SDK with MCP support is required. Install dependency 'openai-agents'."
        ) from exc


def create_codex_mcp_server():
    mcp_server_stdio = _load_mcp_stdio_class()
    return mcp_server_stdio(
        command="codex",
        args=["mcp-server"],
    )


@asynccontextmanager
async def codex_mcp_server() -> AsyncIterator[object]:
    """Open the Codex MCP server for agent tool usage."""

    server = create_codex_mcp_server()
    LOGGER.info("opening_codex_mcp_server")
    async with server:
        yield server
    LOGGER.info("closed_codex_mcp_server")
