"""Checks that must pass before the harness will touch anything: an
active gcloud identity and an open billing account. This is the code
that enforces the scope boundary in docs/architecture.md -- GCP account
and billing signup are the attendee's own pre-workshop responsibility
(docs/prerequisites.md), not something the harness can do for them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from hermes_anvil.mcp.tool_router import GcpToolRouter


@dataclass
class PreflightResult:
    authenticated: bool
    account: str
    in_cloud_shell: bool
    billing_accounts: list[str]

    @property
    def ok(self) -> bool:
        return self.authenticated and bool(self.billing_accounts)


async def run_preflight(router: GcpToolRouter) -> PreflightResult:
    in_cloud_shell = "DEVSHELL_PROJECT_ID" in os.environ

    auth_result = await router.run_gcloud(
        ["auth", "list", "--filter=status:ACTIVE", "--format=value(account)"]
    )
    account = auth_result.stdout.strip()
    authenticated = auth_result.ok and bool(account)

    billing_result = await router.run_gcloud(
        ["billing", "accounts", "list", "--filter=open=true", "--format=value(ACCOUNT_ID)"]
    )
    billing_accounts = [
        line.strip() for line in billing_result.stdout.splitlines() if line.strip()
    ]

    return PreflightResult(
        authenticated=authenticated,
        account=account,
        in_cloud_shell=in_cloud_shell,
        billing_accounts=billing_accounts,
    )
