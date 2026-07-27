from __future__ import annotations

from textual.screen import Screen

from hermes_anvil.gcp.bootstrap import ensure_project
from hermes_anvil.screens._async_step import AsyncStepScreen
from hermes_anvil.theme import STEP_LABELS


class ProjectSetupScreen(AsyncStepScreen):
    label = STEP_LABELS["project_setup"]
    waiting_message = "Setting up project..."

    async def run_step(self) -> str:
        ctx = self.app.ctx
        project_id = await ensure_project(ctx.router, ctx.state, ctx.billing_account)
        return f"Project ready: {project_id}"

    def next_screen(self) -> Screen:
        from hermes_anvil.screens.api_enable import ApiEnableScreen

        return ApiEnableScreen()
