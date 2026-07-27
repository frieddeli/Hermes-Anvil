from __future__ import annotations

from textual.screen import Screen

from hermes_anvil.gcp.identity import ensure_service_account
from hermes_anvil.screens._async_step import AsyncStepScreen
from hermes_anvil.theme import STEP_LABELS


class ServiceAccountScreen(AsyncStepScreen):
    label = STEP_LABELS["service_account"]
    waiting_message = "Creating service account..."

    async def run_step(self) -> str:
        ctx = self.app.ctx
        email = await ensure_service_account(ctx.router, ctx.state)
        return f"Service account ready: {email}"

    def next_screen(self) -> Screen:
        from hermes_anvil.screens.network_security import NetworkSecurityScreen

        return NetworkSecurityScreen()
