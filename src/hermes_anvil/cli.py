"""Entry point: `hermes-anvil` console script / `python -m hermes_anvil`."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

# Must be set before Textual's driver starts (it reads this once, at
# import/startup time via textual.constants). Cloud Shell's web terminal
# (xterm.js) doesn't fully support the Kitty keyboard protocol that
# Textual's Linux driver otherwise enables unconditionally on startup by
# writing a raw "\x1b[>{flags}u" escape sequence -- confirmed by reading
# textual/drivers/linux_driver.py directly. Real-world symptom, reported
# and reproduced: the welcome screen renders fine, but Enter does
# nothing, while the process is still alive (Ctrl+C works normally).
# Known xterm.js gap, not specific to this app: keys like Enter and
# Backspace can get dropped/misidentified under that protocol while
# other keys (letters, arrows, space) keep working.
os.environ.setdefault("TEXTUAL_DISABLE_KITTY_KEY", "1")

from hermes_anvil.app import HermesAnvilApp, RunContext
from hermes_anvil.gcp.secrets import RealSecretWriter
from hermes_anvil.gcp.state import STATE_DIR, RunState
from hermes_anvil.mcp.tool_router import RealGcpToolRouter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hermes-anvil", description="Hatch your own Hermes Agent instance."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run against fake GCP/MCP backends -- no real resources created, $0 cost.",
    )
    parser.add_argument(
        "--resume", metavar="SLUG", help="Resume a previous run by its agent slug."
    )
    parser.add_argument(
        "--allow-public-ip",
        action="store_true",
        help="Pre-select the public-IP option on the network screen (still requires the in-app risk acknowledgment).",
    )
    parser.add_argument(
        "--teardown",
        metavar="SLUG",
        help="Print the command to tear down a previous run's resources.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.teardown:
        print(
            f"Run: scripts/dev_teardown.sh --slug {args.teardown} --project <project-id>"
        )
        return 0

    if args.dry_run:
        from hermes_anvil.dryrun.fakes import FakeGcpToolRouter, FakeSecretWriter

        router = FakeGcpToolRouter()
        secret_writer = FakeSecretWriter()
    else:
        router = RealGcpToolRouter()
        secret_writer = RealSecretWriter()

    ctx = RunContext(
        router=router,
        secret_writer=secret_writer,
        dry_run=args.dry_run,
        state_dir=STATE_DIR / "dry-run" if args.dry_run else STATE_DIR,
        allow_public_ip_flag=args.allow_public_ip,
    )

    if args.resume:
        ctx.state = RunState.load(args.resume, ctx.state_dir)
        if ctx.state is None:
            print(
                f"No saved run found for slug '{args.resume}' in {ctx.state_dir}",
                file=sys.stderr,
            )
            return 1

    asyncio.run(_run_app(ctx))
    return 0


async def _run_app(ctx: RunContext) -> None:
    # The router's MCP clients (gcloud-mcp's stdio subprocess, the
    # Compute Engine MCP's HTTP session) are anyio-based and must be
    # opened and closed within the SAME event loop -- Textual's own
    # App.run() manages its own loop internally and closes it on exit,
    # so calling it here (app.run_async(), inside our own asyncio.run)
    # rather than the sync app.run() is what keeps router.close() in the
    # loop the connections were actually opened in.
    try:
        # mouse=False: Cloud Shell's web-based terminal doesn't cleanly
        # consume Textual's SGR mouse-tracking escape sequences -- they
        # leak through as visible garbage text (e.g. "^[[<0;137;14M")
        # instead of being intercepted. The app is fully keyboard-
        # navigable (Tab/Enter reach every Button), so disabling mouse
        # support costs nothing functionally and avoids this.
        await HermesAnvilApp(ctx).run_async(mouse=False)
    finally:
        await ctx.router.close()


if __name__ == "__main__":
    raise SystemExit(main())
