from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static

from hermes_anvil.gcp.bootstrap import ensure_project
from hermes_anvil.theme import STEP_LABELS


class ProjectSetupScreen(Screen):
    BINDINGS = [Binding("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        with Vertical(classes="step-body"):
            yield Static(STEP_LABELS["project_setup"])
            yield Static("Setting up project...", id="status")

    async def on_mount(self) -> None:
        ctx = self.app.ctx
        status = self.query_one("#status", Static)
        try:
            project_id = await ensure_project(ctx.router, ctx.state, ctx.billing_account)
            status.update(f"Project ready: {project_id}")
            self.set_timer(1.0, self._continue)
        except Exception as e:
            status.update(f"Error: {e}")

    def _continue(self) -> None:
        from hermes_anvil.screens.api_enable import ApiEnableScreen

        self.app.push_screen(ApiEnableScreen())
