"""Client for gcloud-mcp (@google-cloud/gcloud-mcp), spawned as a local
stdio subprocess via `npx`.

Handles everything before the Compute Engine API exists on the project:
project create/select, billing link, API enablement, IAM, firewall rules.
Uses whatever identity is already active via the attendee's own
`gcloud auth`/ADC in Cloud Shell -- no separate auth flow.

Before relying on this in a real workshop run, pin the installed
gcloud-mcp version and confirm its denylist doesn't block `projects
create` / `services enable` / `billing` -- see docs/security.md and the
"Open decisions" section of the approved plan.
"""

from __future__ import annotations

from .client import McpClient
from .tool_router import GcloudResult


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
        result = await self._client.call_tool(
            "run_gcloud_command", {"command": " ".join(args)}
        )
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
