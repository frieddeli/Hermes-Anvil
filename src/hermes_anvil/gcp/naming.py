"""Deterministic, GCP-legal resource names derived from the attendee's
chosen agent name. Every resource in a run shares one `slug`.
"""

from __future__ import annotations

import random
import re
import string

SLUG_MAX_LEN = 20


def slugify(name: str) -> str:
    slug = name.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        slug = "agent"
    # Truncating can land exactly on a hyphen boundary (e.g. "...long-"),
    # which would leave a trailing hyphen -- invalid for GCP resource
    # names -- so strip again after slicing.
    slug = slug[:SLUG_MAX_LEN].rstrip("-")
    return slug or "agent"


def random_suffix(length: int = 4) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def project_id(slug: str, suffix: str | None = None) -> str:
    """GCP project IDs: 6-30 chars, lowercase letters/digits/hyphens,
    must start with a letter, globally unique across all of GCP -- hence
    the random suffix, regenerated on each retry if there's a collision.
    """
    suffix = suffix or random_suffix()
    pid = f"hermes-anvil-{slug}-{suffix}"
    return pid[:30].rstrip("-")


def instance_name(slug: str) -> str:
    return f"hermes-vm-{slug}"[:63]


def service_account_id(slug: str) -> str:
    """Service account IDs: 6-30 chars, lowercase letters/digits/hyphens."""
    sa = f"hermes-vm-{slug}"
    return sa[:30].rstrip("-")


def service_account_email(slug: str, project: str) -> str:
    return f"{service_account_id(slug)}@{project}.iam.gserviceaccount.com"


def firewall_rule_name(slug: str) -> str:
    return f"allow-iap-ssh-{slug}"[:63]


def public_firewall_rule_name(slug: str) -> str:
    return f"allow-public-ssh-{slug}"[:63]


def secret_name(slug: str) -> str:
    return f"hermes-agent-key-{slug}"[:255]
