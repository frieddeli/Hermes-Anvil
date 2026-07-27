"""Entry point: `hermes-anvil` console script / `python -m hermes_anvil`."""

from __future__ import annotations

import argparse
import asyncio
import sys

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

    try:
        HermesAnvilApp(ctx).run()
    finally:
        asyncio.run(router.close())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
