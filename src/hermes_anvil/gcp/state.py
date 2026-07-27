"""Resumable per-run state at ~/.hermes-anvil/<slug>.json.

On any re-run, callers re-verify referenced resources actually exist
(via `describe` calls in bootstrap.py etc.) before trusting
`completed_steps` and skipping ahead -- this file only records what the
harness *believes* happened, not ground truth.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

STATE_DIR = Path.home() / ".hermes-anvil"


@dataclass
class RunState:
    slug: str
    agent_name: str = ""
    project: str = ""
    zone: str = "us-central1-a"
    billing_account: str = ""
    service_account_email: str = ""
    firewall_rule: str = ""
    secret_name: str = ""
    instance_name: str = ""
    allow_public_ip: bool = False
    completed_steps: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Deliberately NOT a dataclass field -- a plain attribute assigned
        # here is excluded from dataclasses.fields()/asdict(), so it never
        # leaks into the persisted JSON. Every gcp/*.py step only has
        # access to a RunState instance (not the CLI's --dry-run flag or
        # ctx.state_dir), so mark_done()/save() need to remember, per
        # instance, which directory THIS run's state belongs to -- set
        # once at load()/load_or_create() time -- rather than silently
        # defaulting to the real global STATE_DIR on every write.
        if not hasattr(self, "_state_dir"):
            self._state_dir = STATE_DIR

    def mark_done(self, step: str) -> None:
        if step not in self.completed_steps:
            self.completed_steps.append(step)
        self.save()

    def is_done(self, step: str) -> bool:
        return step in self.completed_steps

    def path(self, state_dir: Path | None = None) -> Path:
        target = state_dir or self._state_dir
        return target / f"{self.slug}.json"

    def save(self, state_dir: Path | None = None) -> None:
        target = state_dir or self._state_dir
        target.mkdir(parents=True, exist_ok=True)
        self.path(target).write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls, slug: str, state_dir: Path = STATE_DIR) -> "RunState | None":
        path = state_dir / f"{slug}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        instance = cls(**data)
        instance._state_dir = state_dir
        return instance

    @classmethod
    def load_or_create(
        cls, slug: str, agent_name: str, state_dir: Path = STATE_DIR
    ) -> "RunState":
        existing = cls.load(slug, state_dir)
        if existing is not None:
            return existing
        state = cls(slug=slug, agent_name=agent_name)
        state._state_dir = state_dir
        state.save()
        return state
