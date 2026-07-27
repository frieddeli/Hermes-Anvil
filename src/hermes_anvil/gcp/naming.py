"""Deterministic, GCP-legal resource names derived from the user's
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


PROJECT_ID_PREFIX = "hermes-anvil-"


def project_id(slug: str, suffix: str | None = None) -> str:
    """GCP project IDs: 6-30 chars, lowercase letters/digits/hyphens,
    must start with a letter, globally unique across all of GCP -- hence
    the random suffix, regenerated on each retry if there's a collision.

    Truncate the SLUG to make room, not the combined string -- slicing
    the whole "prefix-slug-suffix" string to 30 chars at the end would
    silently chop off (or entirely drop) the suffix for any slug longer
    than ~12 chars (SLUG_MAX_LEN allows up to 20), which both produces
    an ID that isn't actually unique-looking and, worse, makes
    bootstrap.ensure_project's collision-retry loop generate the exact
    same truncated ID on every attempt since the new random suffix never
    survives the slice.
    """
    suffix = suffix or random_suffix()
    max_slug_len = 30 - len(PROJECT_ID_PREFIX) - len(suffix) - 1  # -1 for the "-" before suffix
    trimmed_slug = (slug[:max_slug_len].rstrip("-") or "agent") if max_slug_len > 0 else "a"
    return f"{PROJECT_ID_PREFIX}{trimmed_slug}-{suffix}"


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
