"""Firewall rules. Default path: no public IP, IAP-tunneled SSH only,
scoped to Google's fixed IAP forwarding range. Public-IP is an opt-in
path, only ever called after an explicit risk acknowledgment in the TUI
(docs/security.md, measure 1), and scoped to the user's own /32
rather than 0.0.0.0/0.
"""

from __future__ import annotations

import urllib.request

from hermes_anvil.gcp import naming
from hermes_anvil.gcp.state import RunState
from hermes_anvil.mcp.tool_router import GcpToolRouter

IAP_SOURCE_RANGE = "35.235.240.0/20"


async def ensure_iap_firewall_rule(router: GcpToolRouter, state: RunState) -> str:
    if state.is_done("firewall_created") and state.firewall_rule:
        return state.firewall_rule

    rule_name = naming.firewall_rule_name(state.slug)
    result = await router.run_gcloud(
        [
            "compute",
            "firewall-rules",
            "create",
            rule_name,
            f"--project={state.project}",
            "--direction=INGRESS",
            "--action=ALLOW",
            "--rules=tcp:22",
            f"--source-ranges={IAP_SOURCE_RANGE}",
            f"--target-tags={rule_name}",
        ]
    )
    if not result.ok:
        raise RuntimeError(f"Failed to create IAP firewall rule: {result.stderr}")

    state.firewall_rule = rule_name
    state.mark_done("firewall_created")
    return rule_name


async def ensure_public_ip_firewall_rule(
    router: GcpToolRouter, state: RunState, source_ip: str
) -> str:
    """Only call this after the TUI's explicit public-IP risk acknowledgment."""
    rule_name = naming.public_firewall_rule_name(state.slug)
    result = await router.run_gcloud(
        [
            "compute",
            "firewall-rules",
            "create",
            rule_name,
            f"--project={state.project}",
            "--direction=INGRESS",
            "--action=ALLOW",
            "--rules=tcp:22",
            f"--source-ranges={source_ip}/32",
            f"--target-tags={rule_name}",
        ]
    )
    if not result.ok:
        raise RuntimeError(f"Failed to create public-IP firewall rule: {result.stderr}")
    return rule_name


def detect_public_ip() -> str | None:
    """Best-effort lookup of the user's current public IP, used to
    scope the opt-in public-IP firewall rule to a /32 instead of
    0.0.0.0/0. Returns None on any failure -- callers must handle that
    (e.g. by asking the user to type their IP manually) rather than
    falling back to a wide-open rule.
    """
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as resp:
            ip = resp.read().decode().strip()
        return ip or None
    except Exception:
        return None
