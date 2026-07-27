"""Thin wrapper over the official `mcp` Python SDK.

Provides one async context-managed client that can speak either transport
we need:
  - stdio, for spawning gcloud-mcp as a local subprocess
  - streamable-HTTP, for the Compute Engine remote MCP server

Both `gcloud_server.py` and `compute_server.py` build on this rather than
touching the `mcp` SDK directly, so transport details (session setup,
tool-call plumbing) live in exactly one place.

Deliberately has NO internal timeout handling. An earlier version wrapped
these methods in `anyio.fail_after()` around the `AsyncExitStack`-based
connect logic -- confirmed, by testing against a real running gcloud-mcp
server (not just reasoned about), to break the connection with "Attempted
to exit a cancel scope that isn't the current task's current cancel
scope" EVEN ON THE SUCCESS PATH, not just failures. Bare
`AsyncExitStack.enter_async_context()` (no cancel-scope-based timeout
wrapped around it) was verified working end to end: connect, list_tools,
and close all completed cleanly against a real gcloud-mcp process.
Timeouts belong at the caller boundary instead (see gcloud_server.py /
compute_server.py), wrapping a single complete call with plain
`asyncio.wait_for()` rather than reaching inside this class's
`AsyncExitStack` sequencing.

Refs: anyio cancellation docs (https://anyio.readthedocs.io/en/stable/cancellation.html,
doesn't cover this AsyncExitStack interaction -- found by direct testing,
not documented); `mcp` SDK source read locally in .venv to trace it.
"""

from __future__ import annotations

from contextlib import AsyncExitStack
from typing import Any


class McpClient:
    """A connected MCP session, plus the plumbing to open one."""

    def __init__(self) -> None:
        self._stack = AsyncExitStack()
        self._session: Any = None

    @property
    def session(self) -> Any:
        if self._session is None:
            raise RuntimeError("McpClient used before connect()")
        return self._session

    async def connect_stdio(self, command: str, args: list[str]) -> None:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        params = StdioServerParameters(command=command, args=args)
        read, write = await self._stack.enter_async_context(stdio_client(params))
        session = await self._stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        self._session = session

    async def connect_http(self, url: str, headers: dict[str, str] | None = None) -> None:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        read, write, _get_session_id = await self._stack.enter_async_context(
            streamablehttp_client(url, headers=headers or {})
        )
        session = await self._stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        self._session = session

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        return await self.session.call_tool(name, arguments)

    async def list_tools(self) -> Any:
        return await self.session.list_tools()

    async def close(self) -> None:
        await self._stack.aclose()
        self._session = None

    async def __aenter__(self) -> "McpClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()
