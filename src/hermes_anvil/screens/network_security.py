from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Static

from hermes_anvil.gcp.network import (
    detect_public_ip,
    ensure_iap_firewall_rule,
    ensure_public_ip_firewall_rule,
)


class NetworkSecurityScreen(Screen):
    def compose(self) -> ComposeResult:
        with Vertical(classes="step-body"):
            yield Static("Select network security mode")
            yield Button("Private (recommended)", id="private", variant="primary")
            yield Button("Public IP (advanced)", id="public")
            yield Static(
                "Warning: Public IP makes your VM's SSH port reachable from the "
                "internet, scoped to your own IP only.",
                id="warning",
            )
            yield Input(id="confirm-input", placeholder="Type CONFIRM to proceed")
            yield Input(id="manual-ip", placeholder="Enter your public IP (e.g. 203.0.113.1)")
            yield Static(id="status")

    def on_mount(self) -> None:
        self.query_one("#warning", Static).display = False
        self.query_one("#confirm-input", Input).display = False
        self.query_one("#manual-ip", Input).display = False

        ctx = self.app.ctx
        if ctx.allow_public_ip_flag:
            self.query_one("#public", Button).variant = "primary"
            self.query_one("#private", Button).variant = "default"

    @on(Button.Pressed, "#private")
    async def on_private(self) -> None:
        ctx = self.app.ctx
        status = self.query_one("#status", Static)
        status.update("Configuring IAP firewall rules...")
        await ensure_iap_firewall_rule(ctx.router, ctx.state)
        self._proceed()

    @on(Button.Pressed, "#public")
    def on_public(self) -> None:
        self.query_one("#warning", Static).display = True
        confirm_input = self.query_one("#confirm-input", Input)
        confirm_input.display = True
        confirm_input.focus()

    @on(Input.Submitted, "#confirm-input")
    async def on_confirm(self, event: Input.Submitted) -> None:
        status = self.query_one("#status", Static)
        if event.value != "CONFIRM":
            status.update("You must type CONFIRM exactly to proceed with a public IP.")
            return

        ctx = self.app.ctx
        status.update("Configuring IAP firewall rules...")
        await ensure_iap_firewall_rule(ctx.router, ctx.state)

        status.update("Detecting your public IP...")
        ip = detect_public_ip()
        if ip is None:
            status.update("Could not detect your public IP. Please enter it manually.")
            manual_ip = self.query_one("#manual-ip", Input)
            manual_ip.display = True
            manual_ip.focus()
            return

        await self._configure_public_ip(ip)

    @on(Input.Submitted, "#manual-ip")
    async def on_manual_ip(self, event: Input.Submitted) -> None:
        ip = event.value.strip()
        if not ip:
            return
        await self._configure_public_ip(ip)

    async def _configure_public_ip(self, ip: str) -> None:
        ctx = self.app.ctx
        status = self.query_one("#status", Static)
        status.update(f"Configuring public-IP firewall rules for {ip}...")
        await ensure_public_ip_firewall_rule(ctx.router, ctx.state, ip)
        ctx.state.allow_public_ip = True
        ctx.state.save()
        self._proceed()

    def _proceed(self) -> None:
        from hermes_anvil.screens.secret_setup import SecretSetupScreen

        self.app.push_screen(SecretSetupScreen())
