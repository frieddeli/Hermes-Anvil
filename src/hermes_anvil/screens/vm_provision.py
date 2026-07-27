from __future__ import annotations

from textual.screen import Screen

from hermes_anvil.gcp.compute import provision_instance
from hermes_anvil.screens._async_step import AsyncStepScreen
from hermes_anvil.theme import STEP_LABELS


class VmProvisionScreen(AsyncStepScreen):
    label = STEP_LABELS["vm_provision"]
    waiting_message = "Provisioning VM instance..."

    async def run_step(self) -> str:
        ctx = self.app.ctx
        instance_name = await provision_instance(ctx.router, ctx.state)
        return f"Instance created: {instance_name}"

    def next_screen(self) -> Screen:
        from hermes_anvil.screens.hermes_install_wait import HermesInstallWaitScreen

        return HermesInstallWaitScreen()
