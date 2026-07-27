from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static

from hermes_anvil.gcp.compute import provision_instance
from hermes_anvil.theme import STEP_LABELS


class VmProvisionScreen(Screen):
    BINDINGS = [Binding("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        with Vertical(classes="step-body"):
            yield Static(STEP_LABELS["vm_provision"])
            yield Static("Provisioning VM instance...", id="status")

    async def on_mount(self) -> None:
        ctx = self.app.ctx
        status = self.query_one("#status", Static)
        try:
            instance_name = await provision_instance(ctx.router, ctx.state)
            status.update(f"Instance created: {instance_name}")
            self.set_timer(1.0, self._continue)
        except Exception as e:
            status.update(f"Error: {e}")

    def _continue(self) -> None:
        from hermes_anvil.screens.hermes_install_wait import HermesInstallWaitScreen

        self.app.push_screen(HermesInstallWaitScreen())
