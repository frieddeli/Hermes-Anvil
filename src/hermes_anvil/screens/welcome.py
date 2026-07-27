from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static

from hermes_anvil.theme import ANVIL_ART, WELCOME_TAGLINE


class WelcomeScreen(Screen):
    BINDINGS = [Binding("enter", "begin", "Begin hatching")]

    def compose(self) -> ComposeResult:
        with Vertical(classes="step-body"):
            yield Static(ANVIL_ART, id="anvil-art")
            yield Static(WELCOME_TAGLINE, id="tagline")
            yield Static("\nPress Enter to begin hatching your agent.")

    def action_begin(self) -> None:
        from hermes_anvil.screens.prereq_check import PreflightScreen

        self.app.push_screen(PreflightScreen())
