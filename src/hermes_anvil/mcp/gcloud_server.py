"""Client for gcloud-mcp (@google-cloud/gcloud-mcp), spawned as a local
stdio subprocess via `npx`.

Handles everything before the Compute Engine API exists on the project:
project create/select, billing link, API enablement, IAM, firewall rules.
Uses whatever identity is already active via the user's own
`gcloud auth`/ADC in Cloud Shell -- no separate auth flow.

Verified end to end against a real gcloud-mcp process (with gcloud CLI
present): connects, and `run_gcloud_command` is confirmed as the correct
tool name -- `list_tools()` against a live server returned exactly that.
Its real input schema was also confirmed the hard way: it takes
`{"args": [...]}` (a list), not `{"command": "..."}` (a joined string) --
the latter was the original guess and fails MCP input validation.

Before relying on this in a real run, pin the installed gcloud-mcp
version and confirm its denylist doesn't block `projects create` /
`services enable` / `billing` -- see docs/security.md and the "Open
decisions" section of the approved plan.
"""

from __future__ import annotations

import asyncio

from .client import McpClient
from .tool_router import GcloudResult

# A real Cloud Shell run hung indefinitely with zero feedback on the
# very first gcloud-mcp call -- nothing anywhere had a timeout.
#
# Only wrapped around call_tool, NOT around connect(): testing against a
# real gcloud-mcp process showed wrapping connect_stdio's AsyncExitStack
# entry in asyncio.wait_for() (which spawns its own transient task)
# leaves the connection's long-lived resources bound to that now-gone
# task, breaking close() later with an anyio cancel-scope error --
# confirmed via the production GcloudMcpServer code path, not just in
# isolation. connect() is deliberately left without its own timeout for
# now; call_tool() doesn't create new long-lived resources, so wrapping
# it is safe and was verified working end to end.
CALL_TIMEOUT_SECONDS = 30


class GcloudMcpServer:
    def __init__(self) -> None:
        self._client = McpClient()
        self._connected = False

    async def connect(self) -> None:
        if self._connected:
            return
        await self._client.connect_stdio("npx", ["-y", "@google-cloud/gcloud-mcp"])
        self._connected = True

    async def run_gcloud(self, args: list[str]) -> GcloudResult:
        """Run a gcloud command via gcloud-mcp's `run_gcloud_command` tool.

        `args` excludes the leading `gcloud` -- e.g. ["projects", "create",
        "my-project", "--name=My Project"].
        """
        await self.connect()
        try:
            result = await asyncio.wait_for(
                self._client.call_tool("run_gcloud_command", {"args": args}),
                timeout=CALL_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError as e:
            raise TimeoutError(
                f"Timed out after {CALL_TIMEOUT_SECONDS}s running: gcloud {' '.join(args)}"
            ) from e
        content = _first_text(result)
        is_error = getattr(result, "isError", False)
        return GcloudResult(
            returncode=1 if is_error else 0,
            stdout="" if is_error else content,
            stderr=content if is_error else "",
        )

    async def close(self) -> None:
        if self._connected:
            await self._client.close()
            self._connected = False


def _first_text(result: object) -> str:
    """Pull the first text block out of an MCP CallToolResult."""
    content = getattr(result, "content", None) or []
    for block in content:
        text = getattr(block, "text", None)
        if text is not None:
            return text
    return ""
