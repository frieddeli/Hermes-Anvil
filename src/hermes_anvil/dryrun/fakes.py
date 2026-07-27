"""Fake GcpToolRouter for --dry-run mode.

Simulates the same interface as mcp.tool_router.RealGcpToolRouter, with
configurable latency and injectable failures, so the full attendee flow
(and its resume logic) can be exercised locally at $0 and in CI with no
real GCP credentials.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from hermes_anvil.gcp import naming
from hermes_anvil.gcp.state import RunState
from hermes_anvil.mcp.tool_router import GcloudResult, InstanceInfo, InstanceSpec


@dataclass
class FailureInjection:
    """Make a specific step fail on a specific call, to test resume logic."""

    match: str  # substring to match against the gcloud args (joined) or tool name
    fail_times: int = 1  # how many times to fail before succeeding


@dataclass
class FakeGcpToolRouter:
    latency: float = 0.05
    failures: list[FailureInjection] = field(default_factory=list)
    _projects: set[str] = field(default_factory=set)
    _billing_linked: set[str] = field(default_factory=set)
    _enabled_apis: dict[str, set[str]] = field(default_factory=dict)
    _service_accounts: set[str] = field(default_factory=set)
    _firewall_rules: set[str] = field(default_factory=set)
    _instances: dict[str, InstanceInfo] = field(default_factory=dict)
    _get_calls: dict[str, int] = field(default_factory=dict)
    _call_log: list[str] = field(default_factory=list)

    async def _maybe_fail(self, label: str) -> None:
        await asyncio.sleep(self.latency)
        self._call_log.append(label)
        for injection in self.failures:
            if injection.match in label and injection.fail_times > 0:
                injection.fail_times -= 1
                raise RuntimeError(f"[dry-run injected failure] {label}")

    async def run_gcloud(self, args: list[str]) -> GcloudResult:
        joined = " ".join(args)
        await self._maybe_fail(joined)

        if args[:2] == ["auth", "list"]:
            # Mirrors --format=value(account): one bare value, no header.
            return GcloudResult(0, "dry-run-attendee@example.com")

        if args[:2] == ["projects", "create"]:
            project = args[2]
            self._projects.add(project)
            return GcloudResult(0, f"Created project [{project}].")

        if args[:2] == ["projects", "describe"]:
            project = args[2]
            if project in self._projects:
                return GcloudResult(0, f"projectId: {project}\nlifecycleState: ACTIVE")
            return GcloudResult(1, "", f"NOT_FOUND: project {project} not found")

        if args[:2] == ["billing", "accounts"]:
            # Mirrors --format=value(ACCOUNT_ID): one bare value, no header.
            return GcloudResult(0, "012345-ABCDEF")

        if args[:2] == ["billing", "projects"] and "link" in args:
            project = args[2] if len(args) > 2 else "unknown"
            self._billing_linked.add(project)
            return GcloudResult(0, f"Linked billing account to [{project}].")

        if args[:2] == ["services", "enable"]:
            project = _flag(args, "--project") or "unknown"
            apis = self._enabled_apis.setdefault(project, set())
            for a in args[2:]:
                if not a.startswith("--"):
                    apis.add(a)
            return GcloudResult(0, "Operation finished successfully.")

        if args[:2] == ["services", "list"]:
            project = _flag(args, "--project") or "unknown"
            apis = self._enabled_apis.get(project, set())
            return GcloudResult(0, "\n".join(sorted(apis)))

        if args[:3] == ["iam", "service-accounts", "create"]:
            self._service_accounts.add(args[3])
            return GcloudResult(0, f"Created service account [{args[3]}].")

        if args[:2] == ["compute", "firewall-rules"] and args[2] == "create":
            self._firewall_rules.add(args[3])
            return GcloudResult(0, f"Created firewall rule [{args[3]}].")

        return GcloudResult(0, "")

    async def compute_create_instance(self, spec: InstanceSpec) -> InstanceInfo:
        await self._maybe_fail(f"compute_create_instance:{spec.name}")
        info = InstanceInfo(name=spec.name, status="PROVISIONING", zone=spec.zone)
        self._instances[spec.name] = info
        return info

    async def compute_get_instance(
        self, name: str, zone: str, project: str
    ) -> InstanceInfo:
        await self._maybe_fail(f"compute_get_instance:{name}")
        calls = self._get_calls.get(name, 0) + 1
        self._get_calls[name] = calls
        # Simulate PROVISIONING -> STAGING -> RUNNING over a few polls.
        status = "PROVISIONING" if calls == 1 else "STAGING" if calls == 2 else "RUNNING"
        info = InstanceInfo(name=name, status=status, zone=zone)
        self._instances[name] = info
        return info

    async def close(self) -> None:
        return None


def _flag(args: list[str], name: str) -> str | None:
    prefix = f"{name}="
    for a in args:
        if a.startswith(prefix):
            return a[len(prefix):]
    return None


@dataclass
class FakeSecretWriter:
    """Stands in for gcp.secrets.RealSecretWriter during --dry-run --
    never makes a real Secret Manager call. `written` is exposed only for
    test assertions, never for anything a screen or CLI path should read.
    """

    written: dict[str, str] = field(default_factory=dict)

    def write_api_key(self, state: RunState, api_key: str) -> str:
        secret_id = naming.secret_name(state.slug)
        self.written[secret_id] = api_key
        state.secret_name = secret_id
        state.mark_done("secret_written")
        return secret_id
