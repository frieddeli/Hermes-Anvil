from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Input, Static


class SecretSetupScreen(Screen):
    def compose(self) -> ComposeResult:
        with Vertical(classes="step-body"):
            yield Static(
                "Enter your model-provider API key.\n"
                "This is stored securely in GCP Secret Manager and never shown again."
            )
            yield Input(id="api-key", placeholder="API key", password=True)
            yield Static(id="status")

    @on(Input.Submitted, "#api-key")
    def on_submit(self, event: Input.Submitted) -> None:
        status = self.query_one("#status", Static)
        value = event.value.strip()
        if not value:
            status.update("API key cannot be empty.")
            return

        ctx = self.app.ctx
        ctx.secret_writer.write_api_key(ctx.state, value)

        event.input.value = ""
        value = ""

        from hermes_anvil.screens.vm_provision import VmProvisionScreen

        self.app.push_screen(VmProvisionScreen())
