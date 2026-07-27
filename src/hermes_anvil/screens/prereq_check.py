from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import LoadingIndicator, RichLog, Static

from hermes_anvil import activity_log
from hermes_anvil.gcp.preflight import run_preflight
from hermes_anvil.mcp.client import STDIO_SUBPROCESS_LOG


class PreflightScreen(Screen):
    BINDINGS = [Binding("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        with Vertical(classes="step-body"):
            yield Static("Checking your GCP account...", id="status")
            yield LoadingIndicator(id="spinner")
            # Live feed of gcloud-mcp's own subprocess output -- without
            # this, a slow first-time `npx` package fetch and a genuine
            # hang look identical (a static status line, nothing moving).
            # See activity_log.py for why this exists.
            yield RichLog(id="activity", max_lines=8, wrap=False, highlight=False, markup=False)

    async def on_mount(self) -> None:
        ctx = self.app.ctx
        status = self.query_one("#status", Static)
        self.set_interval(0.15, self._drain_activity_log)

        try:
            result = await run_preflight(ctx.router)
        except Exception as e:
            self.query_one("#spinner", LoadingIndicator).display = False
            status.update(f"Error checking your GCP account: {e}\n\nPress q to quit.")
            return
        self.query_one("#spinner", LoadingIndicator).display = False

        if not result.authenticated:
            status.update(
                "No active gcloud identity found.\n\n"
                "Make sure you're running this in Google Cloud Shell and are "
                "signed in with your Google account. Press q to quit."
            )
            return

        if not result.billing_accounts:
            status.update(
                f"Signed in as {result.account}, but no open GCP billing "
                "account was found.\n\n"
                "Please complete docs/prerequisites.md (activate the GCP "
                "free trial) before running this again. Press q to quit."
            )
            return

        ctx.billing_account = result.billing_accounts[0]
        status.update(
            f"Signed in as {result.account}.\n"
            f"Billing account found: {ctx.billing_account}\n\n"
            "Continuing..."
        )
        self.set_timer(1.0, self._continue)

    def _drain_activity_log(self) -> None:
        log = self.query_one("#activity", RichLog)
        for line in activity_log.poll_file(STDIO_SUBPROCESS_LOG):
            log.write(line)

    def _continue(self) -> None:
        from hermes_anvil.screens.name_your_agent import NameYourAgentScreen

        self.app.push_screen(NameYourAgentScreen())
