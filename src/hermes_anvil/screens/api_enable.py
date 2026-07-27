from __future__ import annotations

from textual.screen import Screen

from hermes_anvil.gcp.bootstrap import enable_apis
from hermes_anvil.screens._async_step import AsyncStepScreen
from hermes_anvil.theme import STEP_LABELS


class ApiEnableScreen(AsyncStepScreen):
    label = STEP_LABELS["api_enable"]
    waiting_message = "Enabling APIs..."

    async def run_step(self) -> str:
        ctx = self.app.ctx
        await enable_apis(ctx.router, ctx.state)
        return "Compute Engine MCP server is now reachable."

    def next_screen(self) -> Screen:
        from hermes_anvil.screens.service_account import ServiceAccountScreen

        return ServiceAccountScreen()
