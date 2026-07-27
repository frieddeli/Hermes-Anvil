"""Dedicated, least-privilege VM service account -- never the default
Compute Engine SA (docs/security.md, measure 2).
"""

from __future__ import annotations

from hermes_anvil.gcp import naming
from hermes_anvil.gcp.state import RunState
from hermes_anvil.mcp.tool_router import GcpToolRouter


async def ensure_service_account(router: GcpToolRouter, state: RunState) -> str:
    if state.is_done("service_account_created") and state.service_account_email:
        return state.service_account_email

    sa_id = naming.service_account_id(state.slug)
    email = naming.service_account_email(state.slug, state.project)

    create = await router.run_gcloud(
        [
            "iam",
            "service-accounts",
            "create",
            sa_id,
            f"--project={state.project}",
            f"--display-name=Hermes Anvil VM ({state.agent_name})",
        ]
    )
    if not create.ok and "ALREADY_EXISTS" not in create.stderr:
        raise RuntimeError(f"Failed to create service account: {create.stderr}")

    logging = await router.run_gcloud(
        [
            "projects",
            "add-iam-policy-binding",
            state.project,
            f"--member=serviceAccount:{email}",
            "--role=roles/logging.logWriter",
        ]
    )
    if not logging.ok:
        raise RuntimeError(f"Failed to grant logging role: {logging.stderr}")

    state.service_account_email = email
    state.mark_done("service_account_created")
    return email


async def grant_secret_access(
    router: GcpToolRouter, state: RunState, secret_id: str
) -> None:
    """Bind the VM's service account to exactly this one secret --
    resource-scoped, not a project-wide Secret Manager role.
    """
    if state.is_done("secret_access_granted"):
        return

    result = await router.run_gcloud(
        [
            "secrets",
            "add-iam-policy-binding",
            secret_id,
            f"--project={state.project}",
            f"--member=serviceAccount:{state.service_account_email}",
            "--role=roles/secretmanager.secretAccessor",
        ]
    )
    if not result.ok:
        raise RuntimeError(f"Failed to grant secret access: {result.stderr}")

    state.mark_done("secret_access_granted")
