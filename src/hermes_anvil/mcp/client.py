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

Every connect/call/close below runs through `_TaskAffineRunner`, not
directly in whatever task calls in -- see that class's docstring for why
this is required, not just defensive. Confirmed live (real crash,
traceback in hand): pressing 'q' to quit while gcloud-mcp was connected
raised "Attempted to exit cancel scope in a different task than it was
entered in" from inside `ctx.router.close()`. Root cause: Textual gives
every mounted Screen its own dedicated asyncio Task, and `connect_stdio()`
had been running lazily inside whichever Screen's `on_mount` called it
first (its cancel scopes bound to *that* task), while `close()` runs in
the app's own outer `asyncio.run()` task, after Textual has already torn
that screen's task down. Same latent bug applies to
`ComputeMcpServer`'s periodic token-refresh reconnect, which calls
`close()` then `connect()` again from whatever screen happens to trigger
the next compute call.
"""

from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Coroutine

# stdio_client() defaults its subprocess's stderr to our own sys.stderr,
# which is the same terminal Textual renders to -- confirmed live: npm's
# own notices and gcloud-mcp's own INFO logs bled directly onto the
# screen, rendering over the TUI instead of being captured. Redirected
# to a log file instead of sys.stderr or /dev/null so the output is
# still available for debugging without polluting the visible terminal.
#
# This must be a plain file object, not a custom write()-only wrapper --
# confirmed live that stdio_client() hands `errlog` to the subprocess
# machinery as a raw OS-level stderr target, which requires a real
# `fileno()`. Child-process writes happen at the fd level and never go
# through a Python object's `write()` at all, so a tee-via-write()
# wrapper both crashes (missing fileno()) and wouldn't have worked
# anyway. Screens that want a live feed tail this file instead --
# see activity_log.py.
STDIO_SUBPROCESS_LOG = Path.home() / ".hermes-anvil" / "mcp-subprocess.log"


class _TaskAffineRunner:
    """Runs every submitted coroutine inside one persistent, dedicated
    asyncio Task, regardless of which task calls `submit()`.

    anyio's cancel scopes (used internally throughout the `mcp` SDK -- the
    session's own background receive loop, the stdio/http transport
    context managers) are bound to whichever asyncio Task entered them;
    exiting one from a different task raises RuntimeError. Textual gives
    every mounted Screen its own dedicated message-pump task, so letting
    `connect()`/`call_tool()`/`close()` each just run in whatever task
    happens to invoke them (a Screen's `on_mount`, this app's own outer
    runner task, a later Screen triggering a reconnect) breaks as soon as
    two of those calls land in different tasks. Funneling everything
    through one task owned here sidesteps it entirely: the caller's task
    identity stops mattering.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[tuple[Coroutine[Any, Any, Any], asyncio.Future[Any]] | None] = (
            asyncio.Queue()
        )
        self._task: asyncio.Task[None] | None = None

    async def _run(self) -> None:
        while True:
            item = await self._queue.get()
            if item is None:
                return
            coro, future = item
            try:
                result = await coro
            except BaseException as e:
                if not future.cancelled():
                    future.set_exception(e)
            else:
                if not future.cancelled():
                    future.set_result(result)

    async def submit(self, coro: Coroutine[Any, Any, Any]) -> Any:
        if self._task is None:
            self._task = asyncio.ensure_future(self._run())
        future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        await self._queue.put((coro, future))
        return await future

    async def stop(self) -> None:
        """Ends the current dedicated task. Safe to `submit()` again
        afterward -- a fresh task is started on demand (needed for
        ComputeMcpServer's close-then-reconnect token refresh)."""
        if self._task is None:
            return
        await self._queue.put(None)
        await self._task
        self._task = None


class McpClient:
    """A connected MCP session, plus the plumbing to open one."""

    def __init__(self) -> None:
        self._stack = AsyncExitStack()
        self._session: Any = None
        self._runner = _TaskAffineRunner()

    @property
    def session(self) -> Any:
        if self._session is None:
            raise RuntimeError("McpClient used before connect()")
        return self._session

    async def connect_stdio(self, command: str, args: list[str]) -> None:
        await self._runner.submit(self._connect_stdio(command, args))

    async def _connect_stdio(self, command: str, args: list[str]) -> None:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        STDIO_SUBPROCESS_LOG.parent.mkdir(parents=True, exist_ok=True)
        errlog = STDIO_SUBPROCESS_LOG.open("a")
        self._stack.callback(errlog.close)

        params = StdioServerParameters(command=command, args=args)
        read, write = await self._stack.enter_async_context(
            stdio_client(params, errlog=errlog)
        )
        session = await self._stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        self._session = session

    async def connect_http(self, url: str, headers: dict[str, str] | None = None) -> None:
        await self._runner.submit(self._connect_http(url, headers))

    async def _connect_http(self, url: str, headers: dict[str, str] | None) -> None:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        read, write, _get_session_id = await self._stack.enter_async_context(
            streamablehttp_client(url, headers=headers or {})
        )
        session = await self._stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        self._session = session

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        return await self._runner.submit(self.session.call_tool(name, arguments))

    async def list_tools(self) -> Any:
        return await self._runner.submit(self.session.list_tools())

    async def close(self) -> None:
        await self._runner.submit(self._stack.aclose())
        await self._runner.stop()
        self._session = None

    async def __aenter__(self) -> "McpClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()
