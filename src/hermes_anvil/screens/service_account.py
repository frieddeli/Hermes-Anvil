from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static

from hermes_anvil.gcp.identity import ensure_service_account
from hermes_anvil.theme import STEP_LABELS


class ServiceAccountScreen(Screen):
    BINDINGS = [Binding("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        with Vertical(classes="step-body"):
            yield Static(STEP_LABELS["service_account"])
            yield Static("Creating service account...", id="status")

    async def on_mount(self) -> None:
        ctx = self.app.ctx
        status = self.query_one("#status", Static)
        try:
            email = await ensure_service_account(ctx.router, ctx.state)
            status.update(f"Service account ready: {email}")
            self.set_timer(1.0, self._continue)
        except Exception as e:
            status.update(f"Error: {e}")

    def _continue(self) -> None:
        from hermes_anvil.screens.network_security import NetworkSecurityScreen

        self.app.push_screen(NetworkSecurityScreen())
