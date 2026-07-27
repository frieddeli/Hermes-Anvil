from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static

from hermes_anvil.gcp.compute import wait_for_running
from hermes_anvil.theme import STEP_LABELS


class HermesInstallWaitScreen(Screen):
    BINDINGS = [Binding("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        with Vertical(classes="step-body"):
            yield Static(STEP_LABELS["hermes_install_wait"])
            yield Static("Waiting for your agent to come online...", id="status")

    async def on_mount(self) -> None:
        ctx = self.app.ctx
        status = self.query_one("#status", Static)
        poll = 0.1 if ctx.dry_run else 5.0
        timeout = 10.0 if ctx.dry_run else 600.0

        try:
            await wait_for_running(ctx.router, ctx.state, poll_interval=poll, timeout=timeout)
            status.update("Your agent is running!")
            self.set_timer(1.0, self._continue)
        except TimeoutError:
            status.update("Timed out waiting for the instance. Check the GCP Console for its status.")
        except Exception as e:
            status.update(f"Error: {e}")

    def _continue(self) -> None:
        from hermes_anvil.screens.hatch_reveal import HatchRevealScreen

        self.app.push_screen(HatchRevealScreen())
