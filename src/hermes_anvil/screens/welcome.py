from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static

from hermes_anvil.theme import ANVIL_ART, WELCOME_TAGLINE
from hermes_anvil.version_info import build_label


class WelcomeScreen(Screen):
    BINDINGS = [Binding("enter", "begin", "Begin hatching")]

    def compose(self) -> ComposeResult:
        with Vertical(classes="step-body"):
            yield Static(ANVIL_ART, id="anvil-art")
            yield Static(WELCOME_TAGLINE, id="tagline")
            yield Static("\nPress Enter to begin hatching your agent.")
            # Shown small and dim, deliberately -- exists so a screenshot
            # unambiguously answers "which build is this" rather than
            # guessing from behavior alone, after more than one round of
            # a fix not actually reaching a real Cloud Shell test.
            yield Static(f"\n[dim]{build_label()}[/dim]", id="build-label")

    def action_begin(self) -> None:
        from hermes_anvil.screens.prereq_check import PreflightScreen

        self.app.push_screen(PreflightScreen())
