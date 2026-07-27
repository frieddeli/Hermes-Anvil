"""VM provisioning: render the startup script, create the instance via
the Compute Engine MCP server, poll until RUNNING.
"""

from __future__ import annotations

import asyncio
from importlib import resources

from jinja2 import Template

from hermes_anvil.gcp import naming
from hermes_anvil.gcp.state import RunState
from hermes_anvil.mcp.tool_router import GcpToolRouter, InstanceSpec

DEFAULT_ZONE = "us-central1-a"
DEFAULT_POLL_INTERVAL_SECONDS = 5
DEFAULT_POLL_TIMEOUT_SECONDS = 600


def render_startup_script(state: RunState) -> str:
    template_path = resources.files("hermes_anvil.gcp").joinpath("startup_script.sh.j2")
    template = Template(template_path.read_text())
    return template.render(
        project=state.project,
        secret_name=state.secret_name,
        agent_name=state.agent_name,
    )


async def provision_instance(router: GcpToolRouter, state: RunState) -> str:
    if state.is_done("instance_created") and state.instance_name:
        return state.instance_name

    name = naming.instance_name(state.slug)
    zone = state.zone or DEFAULT_ZONE
    startup_script = render_startup_script(state)

    spec = InstanceSpec(
        name=name,
        project=state.project,
        zone=zone,
        service_account_email=state.service_account_email,
        network_tags=[state.firewall_rule] if state.firewall_rule else [],
        external_ip=state.allow_public_ip,
        startup_script=startup_script,
    )
    await router.compute_create_instance(spec)

    state.instance_name = name
    state.zone = zone
    state.mark_done("instance_created")
    return name


async def wait_for_running(
    router: GcpToolRouter,
    state: RunState,
    poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
    timeout: float = DEFAULT_POLL_TIMEOUT_SECONDS,
) -> None:
    if state.is_done("instance_running"):
        return

    elapsed = 0.0
    while elapsed < timeout:
        info = await router.compute_get_instance(state.instance_name, state.zone, state.project)
        if info.status == "RUNNING":
            state.mark_done("instance_running")
            return
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    raise TimeoutError(
        f"Instance {state.instance_name} did not reach RUNNING within {timeout}s"
    )
