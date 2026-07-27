"""Project creation, billing link, and API enablement -- the gcloud-mcp
steps that have to happen before the Compute Engine remote MCP server
becomes reachable (see docs/architecture.md).
"""

from __future__ import annotations

from hermes_anvil.gcp import naming
from hermes_anvil.gcp.state import RunState
from hermes_anvil.mcp.tool_router import GcpToolRouter

REQUIRED_APIS = [
    "compute.googleapis.com",
    "iap.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
]

MAX_PROJECT_CREATE_ATTEMPTS = 5


async def ensure_project(
    router: GcpToolRouter, state: RunState, billing_account: str
) -> str:
    if state.project:
        describe = await router.run_gcloud(["projects", "describe", state.project])
        if describe.ok:
            # The project itself surviving a crash doesn't mean billing
            # got linked -- a crash between mark_done("project_created")
            # and the link call below would otherwise be resumed as if
            # billing were already handled, and enable_apis would then
            # fail on an unlinked project with a confusing GCP error
            # instead of a clear one.
            if not state.is_done("billing_linked"):
                await _link_billing(router, state, billing_account)
            return state.project
        # Referenced project no longer exists -- fall through and create anew.

    project = naming.project_id(state.slug)
    for _ in range(MAX_PROJECT_CREATE_ATTEMPTS):
        create = await router.run_gcloud(
            ["projects", "create", project, f"--name=Hermes Anvil - {state.agent_name}"]
        )
        if create.ok:
            break
        project = naming.project_id(state.slug)  # new random suffix, retry
    else:
        raise RuntimeError(
            f"Could not create a uniquely-named GCP project after "
            f"{MAX_PROJECT_CREATE_ATTEMPTS} attempts"
        )

    state.project = project
    state.mark_done("project_created")

    await _link_billing(router, state, billing_account)
    return project


async def _link_billing(router: GcpToolRouter, state: RunState, billing_account: str) -> None:
    link = await router.run_gcloud(
        ["billing", "projects", "link", state.project, f"--billing-account={billing_account}"]
    )
    if not link.ok:
        raise RuntimeError(f"Failed to link billing account: {link.stderr}")

    state.billing_account = billing_account
    state.mark_done("billing_linked")


async def enable_apis(router: GcpToolRouter, state: RunState) -> None:
    if state.is_done("apis_enabled"):
        return

    result = await router.run_gcloud(
        ["services", "enable", *REQUIRED_APIS, f"--project={state.project}"]
    )
    if not result.ok:
        raise RuntimeError(f"Failed to enable APIs: {result.stderr}")

    state.mark_done("apis_enabled")
