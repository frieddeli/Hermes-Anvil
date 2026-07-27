from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static


class HandoffSummaryScreen(Screen):
    BINDINGS = [Binding("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        with Vertical(classes="step-body"):
            yield Static(id="summary")

    def on_mount(self) -> None:
        ctx = self.app.ctx
        state = ctx.state

        doc_content = (
            f"# {state.agent_name} handoff summary\n\n"
            f"## Reconnect command\n"
            f"gcloud compute ssh {state.instance_name} --zone {state.zone} "
            f"--tunnel-through-iap --project {state.project}\n\n"
            f"## Check logs\n"
            f"sudo journalctl -u hermes-agent -f\n\n"
            f"## API key rotation\n"
            f"The model-provider API key can be rotated by updating the Secret "
            f"Manager secret named:\n{state.secret_name}\n\n"
            f"## Teardown\n"
            f"Running `hermes-anvil --teardown {state.slug}` will show the "
            f"teardown command.\n\n"
            f"## Self-managing its own VM via MCP\n"
            f"Not set up by default -- this is available to wire up yourself "
            f"later if you want your agent to inspect/manage its own VM.\n\n"
            f"## Google Workspace MCP (Gmail / Calendar / Drive / Chat)\n"
            f"A ready-to-uncomment config block is already staged, commented "
            f"out, in ~/.hermes/config.yaml on the VM.\n"
        )

        doc_path = Path.home() / f"hermes-anvil-{state.slug}-handoff.md"
        doc_path.write_text(doc_content)

        summary_text = (
            f"Agent '{state.agent_name}' provisioning complete!\n\n"
            f"A detailed handoff document has been saved to:\n{doc_path}\n\n"
            f"Press q to quit."
        )
        self.query_one("#summary", Static).update(summary_text)

    def action_quit(self) -> None:
        self.app.exit()
