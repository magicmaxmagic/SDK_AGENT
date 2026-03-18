from __future__ import annotations

from contextlib import asynccontextmanager

from agents.mcp import MCPServerStdio


def create_codex_mcp_server() -> MCPServerStdio:
    return MCPServerStdio(
        command="codex",
        args=["mcp-server"],
    )


@asynccontextmanager
async def codex_mcp_server():
    server = create_codex_mcp_server()
    async with server:
        yield server
