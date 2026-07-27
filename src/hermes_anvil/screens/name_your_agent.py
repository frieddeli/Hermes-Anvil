from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Input, Static

from hermes_anvil.gcp.naming import slugify
from hermes_anvil.gcp.state import RunState


class NameYourAgentScreen(Screen):
    def compose(self) -> ComposeResult:
        with Vertical(classes="step-body"):
            yield Static("What would you like to name your agent?")
            yield Input(id="agent-name", placeholder="e.g. Athena")
            yield Static(id="status")

    @on(Input.Submitted, "#agent-name")
    def on_submit(self, event: Input.Submitted) -> None:
        status = self.query_one("#status", Static)
        name = event.value.strip()
        if not name:
            status.update("Agent name cannot be empty.")
            return

        ctx = self.app.ctx
        slug = slugify(name)
        ctx.state = RunState.load_or_create(slug, name, ctx.state_dir)

        from hermes_anvil.screens.project_setup import ProjectSetupScreen

        self.app.push_screen(ProjectSetupScreen())
