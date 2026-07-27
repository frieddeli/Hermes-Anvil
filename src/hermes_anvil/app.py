"""Textual App: screen-stack orchestrator and shared run context.

Screens read/write `self.app.ctx` (a `RunContext`) rather than passing
state through constructors, since the user flow is a strict linear
sequence of full-screen steps (see docs/architecture.md) and every
screen after `name_your_agent` needs the same handful of shared values
(the router, the in-progress `RunState`, dry-run flag, etc).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from textual.app import App

from hermes_anvil.gcp.secrets import SecretWriter
from hermes_anvil.gcp.state import STATE_DIR, RunState
from hermes_anvil.mcp.tool_router import GcpToolRouter


@dataclass
class RunContext:
    router: GcpToolRouter
    secret_writer: SecretWriter
    dry_run: bool = False
    state_dir: Path = STATE_DIR
    allow_public_ip_flag: bool = False  # --allow-public-ip: skip straight to that path in network_security
    billing_account: str = ""  # set by PreflightScreen once preflight finds an open billing account
    state: RunState | None = None
    api_key: str = ""  # held only transiently between secret_setup and the write call


class HermesAnvilApp(App):
    TITLE = "Hermes Anvil"
    CSS = """
    Screen {
        align: center middle;
    }
    #anvil-art, #hatch-art {
        text-align: center;
        color: $primary;
    }
    .step-body {
        width: 80%;
        max-width: 100;
    }
    """

    def __init__(self, ctx: RunContext) -> None:
        super().__init__()
        self.ctx = ctx

    def on_mount(self) -> None:
        from hermes_anvil.screens.welcome import WelcomeScreen

        self.push_screen(WelcomeScreen())
