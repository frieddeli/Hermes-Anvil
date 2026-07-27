import hermes_anvil.mcp.compute_server as compute_server_module
import hermes_anvil.mcp.gcloud_server as gcloud_server_module
import pytest
from hermes_anvil.mcp.tool_router import (
    GcloudResult,
    InstanceInfo,
    InstanceSpec,
    RealGcpToolRouter,
)


def test_gcloud_result_ok():
    assert GcloudResult(0, "ok").ok is True
    assert GcloudResult(1, "", "boom").ok is False


class _StubGcloud:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.closed = False

    async def run_gcloud(self, args: list[str]) -> GcloudResult:
        self.calls.append(args)
        return GcloudResult(0, "stub-output")

    async def close(self) -> None:
        self.closed = True


class _StubCompute:
    def __init__(self) -> None:
        self.create_calls: list[InstanceSpec] = []
        self.get_calls: list[tuple[str, str, str]] = []
        self.closed = False

    async def compute_create_instance(self, spec: InstanceSpec) -> InstanceInfo:
        self.create_calls.append(spec)
        return InstanceInfo(name=spec.name, status="PROVISIONING", zone=spec.zone)

    async def compute_get_instance(self, name: str, zone: str, project: str) -> InstanceInfo:
        self.get_calls.append((name, zone, project))
        return InstanceInfo(name=name, status="RUNNING", zone=zone)

    async def close(self) -> None:
        self.closed = True


@pytest.fixture
def stub_servers(monkeypatch):
    stub_gcloud = _StubGcloud()
    stub_compute = _StubCompute()
    # RealGcpToolRouter.__init__ does `from .gcloud_server import GcloudMcpServer`
    # / `from .compute_server import ComputeMcpServer` at call time, so patching
    # the class attribute on each origin module is picked up on construction.
    monkeypatch.setattr(gcloud_server_module, "GcloudMcpServer", lambda: stub_gcloud)
    monkeypatch.setattr(compute_server_module, "ComputeMcpServer", lambda: stub_compute)
    return stub_gcloud, stub_compute


async def test_real_router_delegates_run_gcloud(stub_servers):
    stub_gcloud, _ = stub_servers
    router = RealGcpToolRouter()

    result = await router.run_gcloud(["projects", "list"])

    assert result.stdout == "stub-output"
    assert stub_gcloud.calls == [["projects", "list"]]


async def test_real_router_delegates_compute_calls(stub_servers):
    _, stub_compute = stub_servers
    router = RealGcpToolRouter()
    spec = InstanceSpec(name="vm1", project="p", zone="z")

    created = await router.compute_create_instance(spec)
    assert created.name == "vm1"
    assert stub_compute.create_calls == [spec]

    info = await router.compute_get_instance("vm1", "z", "p")
    assert info.status == "RUNNING"
    assert stub_compute.get_calls == [("vm1", "z", "p")]


async def test_real_router_close_closes_both(stub_servers):
    stub_gcloud, stub_compute = stub_servers
    router = RealGcpToolRouter()

    await router.close()

    assert stub_gcloud.closed is True
    assert stub_compute.closed is True
