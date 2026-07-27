"""Direct Secret Manager SDK calls -- the one deliberate exception to
"route everything through MCP". See docs/security.md, measure 3: a raw
API key must never touch a subprocess CLI, shell history, or `ps`
output, so this talks to the Secret Manager API in-process instead of
going through gcloud-mcp.

`SecretWriter` is a Protocol so `dryrun.fakes.FakeSecretWriter` can stand
in during --dry-run without ever making a real API call.
"""

from __future__ import annotations

from typing import Protocol

from hermes_anvil.gcp import naming
from hermes_anvil.gcp.state import RunState


class SecretWriter(Protocol):
    def write_api_key(self, state: RunState, api_key: str) -> str: ...


class RealSecretWriter:
    def write_api_key(self, state: RunState, api_key: str) -> str:
        from google.api_core.exceptions import AlreadyExists
        from google.cloud import secretmanager

        secret_id = naming.secret_name(state.slug)
        client = secretmanager.SecretManagerServiceClient()
        parent = f"projects/{state.project}"
        secret_resource_name = f"{parent}/secrets/{secret_id}"

        try:
            secret = client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
            secret_resource_name = secret.name
        except AlreadyExists:
            # Resumed run: create_secret succeeded on a prior attempt but
            # add_secret_version below never got the chance to run (or
            # mark_done never ran) before a crash -- retry from here
            # instead of failing on a name collision.
            pass

        client.add_secret_version(
            request={
                "parent": secret_resource_name,
                "payload": {"data": api_key.encode("utf-8")},
            }
        )

        state.secret_name = secret_id
        state.mark_done("secret_written")
        return secret_id
