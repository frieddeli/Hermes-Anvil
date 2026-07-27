"""Single source of truth for which backend handles which GCP operation.

Two real MCP servers sit behind this router (see docs/architecture.md):

- gcloud-mcp (local stdio subprocess) handles anything before the Compute
  Engine API exists on the project: project create/select, billing link,
  API enablement, IAM, firewall rules.
- The Compute Engine remote MCP server (https://compute.googleapis.com/mcp)
  takes over for VM lifecycle once that API is enabled.

Secret Manager writes deliberately bypass both and go straight to the
Secret Manager SDK in-process -- see docs/security.md, measure 3, for why.

`GcpToolRouter` is a Protocol so `dryrun/fakes.py` can provide a fake
implementation with the exact same shape, letting every `gcp/*.py` module
be written once and run against either backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class GcloudResult:
    """Result of a single gcloud-mcp `run_gcloud_command` call."""

    returncode: int
    stdout: str
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0


@dataclass
class InstanceSpec:
    name: str
    project: str
    zone: str
    machine_type: str = "e2-small"
    disk_size_gb: int = 20
    disk_type: str = "pd-balanced"
    service_account_email: str = ""
    network_tags: list[str] = field(default_factory=list)
    external_ip: bool = False
    startup_script: str = ""
    shielded_vm: bool = True


@dataclass
class InstanceInfo:
    name: str
    status: str  # PROVISIONING | STAGING | RUNNING | STOPPING | TERMINATED
    zone: str


class GcpToolRouter(Protocol):
    """The interface every `gcp/*.py` module is written against."""

    async def run_gcloud(self, args: list[str]) -> GcloudResult:
        """Run a gcloud command via gcloud-mcp's run_gcloud_command tool."""
        ...

    async def compute_create_instance(self, spec: InstanceSpec) -> InstanceInfo:
        """Create a VM via the Compute Engine remote MCP server."""
        ...

    async def compute_get_instance(
        self, name: str, zone: str, project: str
    ) -> InstanceInfo:
        """Fetch current instance status via the Compute Engine remote MCP server."""
        ...

    async def close(self) -> None:
        """Release any open MCP client connections/subprocesses."""
        ...


class RealGcpToolRouter:
    """Live implementation: gcloud-mcp for bootstrap, Compute Engine MCP for VMs.

    This is the concrete class the two MCP server clients in this table
    correspond to:

    | Step | Server |
    |---|---|
    | project create/select, billing link, API enable, IAM, firewall | gcloud-mcp |
    | VM instance create/get | Compute Engine remote MCP server |
    """

    def __init__(self) -> None:
        from .compute_server import ComputeMcpServer
        from .gcloud_server import GcloudMcpServer

        self._gcloud = GcloudMcpServer()
        self._compute = ComputeMcpServer()

    async def run_gcloud(self, args: list[str]) -> GcloudResult:
        return await self._gcloud.run_gcloud(args)

    async def compute_create_instance(self, spec: InstanceSpec) -> InstanceInfo:
        return await self._compute.compute_create_instance(spec)

    async def compute_get_instance(
        self, name: str, zone: str, project: str
    ) -> InstanceInfo:
        return await self._compute.compute_get_instance(name, zone, project)

    async def close(self) -> None:
        await self._gcloud.close()
        await self._compute.close()
