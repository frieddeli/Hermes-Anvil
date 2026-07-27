"""End-to-end smoke test driving the actual Textual app through every
screen with simulated keypresses, against dry-run fakes. Unlike
test_dryrun_flow.py (which calls gcp/*.py functions directly), this
exercises the screens themselves -- widget IDs, transitions, CSS -- none
of which the unit tests touch.
"""

from __future__ import annotations

from pathlib import Path

from hermes_anvil.app import HermesAnvilApp, RunContext
from hermes_anvil.dryrun.fakes import FakeGcpToolRouter, FakeSecretWriter


async def test_full_attendee_flow_via_pilot(tmp_path):
    ctx = RunContext(
        router=FakeGcpToolRouter(latency=0),
        secret_writer=FakeSecretWriter(),
        dry_run=True,
        state_dir=tmp_path,
    )
    app = HermesAnvilApp(ctx)

    async with app.run_test() as pilot:
        # Welcome -> prereq_check
        await pilot.press("enter")
        await pilot.pause()

        # prereq_check auto-runs preflight then waits 1s before continuing
        await pilot.pause(1.2)

        # name_your_agent: type a name, submit
        await pilot.click("#agent-name")
        await pilot.press(*"Athena")
        await pilot.press("enter")
        await pilot.pause()
        assert ctx.state is not None
        assert ctx.state.agent_name == "Athena"
        assert ctx.state.slug == "athena"

        # project_setup -> api_enable -> service_account, each auto + 1s pause
        await pilot.pause(1.2)  # project_setup
        await pilot.pause(1.2)  # api_enable
        await pilot.pause(1.2)  # service_account

        # network_security: choose Private
        await pilot.click("#private")
        await pilot.pause()
        assert ctx.state.firewall_rule

        # secret_setup: type a key, submit
        await pilot.click("#api-key")
        await pilot.press(*"sk-fake-123")
        await pilot.press("enter")
        await pilot.pause()
        assert ctx.state.secret_name
        assert ctx.secret_writer.written[ctx.state.secret_name] == "sk-fake-123"

        # vm_provision -> hermes_install_wait, each auto + 1s pause
        await pilot.pause(1.2)  # vm_provision
        await pilot.pause(1.2)  # hermes_install_wait (dry_run polling is fast)

        assert ctx.state.instance_name
        assert ctx.state.is_done("instance_running")

        # hatch_reveal -> handoff_summary
        await pilot.press("enter")
        await pilot.pause()

        handoff_path = Path.home() / f"hermes-anvil-{ctx.state.slug}-handoff.md"
        assert handoff_path.exists()
        content = handoff_path.read_text()
        assert "gcloud compute ssh" in content
        assert ctx.state.instance_name in content
        handoff_path.unlink()  # clean up -- this test writes to the real home dir

        await pilot.press("q")
