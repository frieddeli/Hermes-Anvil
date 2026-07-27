"""Client for the official Compute Engine remote MCP server
(https://compute.googleapis.com/mcp).

Only reachable once `compute.googleapis.com` is enabled on the project --
gcloud_server.py handles everything before that point. Auth is OAuth2/ADC;
the bearer token needs an hourly refresh, which this class handles by
tracking connection age and transparently reconnecting with a fresh
token (via `gcloud auth print-access-token`) once it's past
TOKEN_REFRESH_INTERVAL_SECONDS, rather than caching the token forever.

NOTE: the exact tool names below are unconfirmed, and two independent
research passes gave CONFLICTING answers -- a direct fetch of Google's
docs page found no explicit tool-name list at all, while a separate
pass claimed to find one listing different, snake_case names
(create_instance, get_instance_basic_info, etc). Do not trust either
version over the other; call `list_tools()` against the live server
with real credentials before the first real end-to-end run and use
whatever it actually returns. See docs/dev-guide.md, gap #1, for the
full detail. This module is written so that's a one-place fix.
"""

from __future__ import annotations

import asyncio
import time

from .client import McpClient
from .tool_router import InstanceInfo, InstanceSpec

COMPUTE_MCP_URL = "https://compute.googleapis.com/mcp"

# Best-effort tool names pending live verification -- see module docstring.
TOOL_CREATE_INSTANCE = "compute.instances.insert"
TOOL_GET_INSTANCE = "compute.instances.get"

# GCP access tokens are typically valid ~60 minutes; refresh with margin
# to spare rather than waiting for an actual 401.
TOKEN_REFRESH_INTERVAL_SECONDS = 50 * 60


class ComputeMcpServer:
    def __init__(self) -> None:
        self._client = McpClient()
        self._connected = False
        self._connected_at: float = 0.0

    async def _access_token(self) -> str:
        proc = await asyncio.create_subprocess_exec(
            "gcloud",
            "auth",
            "print-access-token",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"gcloud auth print-access-token failed: {stderr.decode()}")
        return stdout.decode().strip()

    async def connect(self) -> None:
        if self._connected:
            return
        token = await self._access_token()
        await self._client.connect_http(
            COMPUTE_MCP_URL, headers={"Authorization": f"Bearer {token}"}
        )
        self._connected = True
        self._connected_at = time.monotonic()

    async def _reconnect(self) -> None:
        """Refresh the bearer token and reopen the session (hourly expiry)."""
        await self._client.close()
        self._connected = False
        await self.connect()

    async def _ensure_fresh_connection(self) -> None:
        if not self._connected:
            await self.connect()
            return
        if time.monotonic() - self._connected_at > TOKEN_REFRESH_INTERVAL_SECONDS:
            await self._reconnect()

    async def compute_create_instance(self, spec: InstanceSpec) -> InstanceInfo:
        await self._ensure_fresh_connection()
        body = {
            "name": spec.name,
            "machineType": f"zones/{spec.zone}/machineTypes/{spec.machine_type}",
            "disks": [
                {
                    "boot": True,
                    "autoDelete": True,
                    "initializeParams": {
                        "diskSizeGb": str(spec.disk_size_gb),
                        "diskType": f"zones/{spec.zone}/diskTypes/{spec.disk_type}",
                        "sourceImage": "projects/debian-cloud/global/images/family/debian-12",
                    },
                }
            ],
            "networkInterfaces": [
                {"accessConfigs": [{"type": "ONE_TO_ONE_NAT"}]} if spec.external_ip else {}
            ],
            "tags": {"items": spec.network_tags},
            "serviceAccounts": [
                {
                    "email": spec.service_account_email,
                    "scopes": ["https://www.googleapis.com/auth/cloud-platform"],
                }
            ],
            "metadata": {
                "items": [{"key": "startup-script", "value": spec.startup_script}]
            },
            "shieldedInstanceConfig": {
                "enableSecureBoot": spec.shielded_vm,
                "enableVtpm": spec.shielded_vm,
                "enableIntegrityMonitoring": spec.shielded_vm,
            },
        }
        await self._client.call_tool(
            TOOL_CREATE_INSTANCE,
            {"project": spec.project, "zone": spec.zone, "instanceResource": body},
        )
        return InstanceInfo(name=spec.name, status="PROVISIONING", zone=spec.zone)

    async def compute_get_instance(
        self, name: str, zone: str, project: str
    ) -> InstanceInfo:
        await self._ensure_fresh_connection()
        result = await self._client.call_tool(
            TOOL_GET_INSTANCE, {"project": project, "zone": zone, "instance": name}
        )
        status = _extract_status(result)
        return InstanceInfo(name=name, status=status, zone=zone)

    async def close(self) -> None:
        if self._connected:
            await self._client.close()
            self._connected = False


def _extract_status(result: object) -> str:
    content = getattr(result, "content", None) or []
    for block in content:
        text = getattr(block, "text", None)
        if text and "RUNNING" in text:
            return "RUNNING"
        if text and "TERMINATED" in text:
            return "TERMINATED"
    return "PROVISIONING"
