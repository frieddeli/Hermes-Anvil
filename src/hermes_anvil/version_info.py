"""Resolves exactly which build is running, for diagnosing "did my fix
actually reach the user" questions without guessing.

For a `uvx --from git+https://...` install (how attendees actually run
this), pip/uv record the resolved commit SHA in the installed package's
own direct_url.json -- confirmed by inspecting a real uv cache entry:
{"url": "...", "vcs_info": {"vcs": "git", "commit_id": "<full SHA>"}}.
"""

from __future__ import annotations

import json
from importlib import metadata

from hermes_anvil import __version__


def build_label() -> str:
    """A short, human-readable label identifying exactly what's running,
    e.g. "0.1.0 (git 8ae8c06)" or "0.1.0 (editable/dev install)"."""
    commit = _resolved_git_commit()
    if commit:
        return f"{__version__} (git {commit[:7]})"
    return f"{__version__} (non-git install)"


def _resolved_git_commit() -> str | None:
    try:
        dist = metadata.distribution("hermes-anvil")
        raw = dist.read_text("direct_url.json")
        if raw is None:
            return None
        data = json.loads(raw)
        return data.get("vcs_info", {}).get("commit_id")
    except Exception:
        return None
