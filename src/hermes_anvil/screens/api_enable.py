from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static

from hermes_anvil.gcp.bootstrap import enable_apis
from hermes_anvil.theme import STEP_LABELS


class ApiEnableScreen(Screen):
    BINDINGS = [Binding("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        with Vertical(classes="step-body"):
            yield Static(STEP_LABELS["api_enable"])
            yield Static("Enabling APIs...", id="status")

    async def on_mount(self) -> None:
        ctx = self.app.ctx
        status = self.query_one("#status", Static)
        try:
            await enable_apis(ctx.router, ctx.state)
            status.update("Compute Engine MCP server is now reachable.")
            self.set_timer(1.0, self._continue)
        except Exception as e:
            status.update(f"Error: {e}")

    def _continue(self) -> None:
        from hermes_anvil.screens.service_account import ServiceAccountScreen

        self.app.push_screen(ServiceAccountScreen())
