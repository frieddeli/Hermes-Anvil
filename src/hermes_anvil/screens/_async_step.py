"""Shared base for screens that run one async GCP step, then auto-advance.

project_setup / api_enable / service_account / vm_provision /
hermes_install_wait were all the same shape already: a label, a status
line, run one async call in on_mount, update the status, wait a beat,
push the next screen. Pulling that into one place also fixes a real UX
gap: with just a static status line, a slow-but-healthy multi-second (or
for VM boot, multi-minute) wait looked identical to a genuine hang --
nothing on screen moved. Every subclass now gets an animated
LoadingIndicator for free while its step is in flight.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import LoadingIndicator, Static


class AsyncStepScreen(Screen):
    BINDINGS = [Binding("q", "quit", "Quit")]

    label: str = ""
    waiting_message: str = "Working..."

    def compose(self) -> ComposeResult:
        with Vertical(classes="step-body"):
            if self.label:
                yield Static(self.label)
            yield Static(self.waiting_message, id="status")
            yield LoadingIndicator(id="spinner")

    async def run_step(self) -> str:
        """Do the work; return the status message to show on success."""
        raise NotImplementedError

    def next_screen(self) -> Screen:
        raise NotImplementedError

    async def on_mount(self) -> None:
        status = self.query_one("#status", Static)
        try:
            message = await self.run_step()
        except Exception as e:
            self.query_one("#spinner", LoadingIndicator).display = False
            status.update(f"Error: {e}")
            return
        self.query_one("#spinner", LoadingIndicator).display = False
        status.update(message)
        self.set_timer(1.0, self._continue)

    def _continue(self) -> None:
        self.app.push_screen(self.next_screen())
