from __future__ import annotations

from textual.screen import Screen

from hermes_anvil.gcp.compute import wait_for_running
from hermes_anvil.screens._async_step import AsyncStepScreen
from hermes_anvil.theme import STEP_LABELS


class HermesInstallWaitScreen(AsyncStepScreen):
    label = STEP_LABELS["hermes_install_wait"]
    waiting_message = "Waiting for your agent to come online..."

    async def run_step(self) -> str:
        ctx = self.app.ctx
        poll = 0.1 if ctx.dry_run else 5.0
        timeout = 10.0 if ctx.dry_run else 600.0
        await wait_for_running(ctx.router, ctx.state, poll_interval=poll, timeout=timeout)
        return "Your agent is running!"

    def next_screen(self) -> Screen:
        from hermes_anvil.screens.hatch_reveal import HatchRevealScreen

        return HatchRevealScreen()
