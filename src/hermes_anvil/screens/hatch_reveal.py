from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static

from hermes_anvil.theme import HATCH_ART


class HatchRevealScreen(Screen):
    BINDINGS = [Binding("enter", "continue", "Continue")]

    def compose(self) -> ComposeResult:
        with Vertical(classes="step-body"):
            yield Static(HATCH_ART, id="hatch-art")
            yield Static(id="message")

    def on_mount(self) -> None:
        ctx = self.app.ctx
        name = ctx.state.agent_name
        self.query_one("#message", Static).update(f"{name} has hatched!")

    def action_continue(self) -> None:
        from hermes_anvil.screens.handoff_summary import HandoffSummaryScreen

        self.app.push_screen(HandoffSummaryScreen())
