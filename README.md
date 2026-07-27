# Hermes Anvil

A guided deployment harness for a "hatch your own agent" workshop. Each attendee runs one command in Google Cloud Shell and comes out the other side owning a live, running instance of [Hermes Agent](https://github.com/nousresearch/hermes-agent) in their own GCP project — theirs to keep and take home.

## What this is

Hermes Anvil is the harness, not the agent. It's an interactive terminal wizard (TUI) that an attendee runs in Cloud Shell, which:

1. Verifies they already have GCP billing enabled (a pre-workshop prerequisite — see [docs/prerequisites.md](docs/prerequisites.md)).
2. Creates their GCP project, enables the required APIs, and sets up a least-privilege service account, network rules, and a Secret Manager entry for their model-provider API key.
3. Provisions a small VM and installs Hermes Agent on it.
4. Hands off a connection guide and next steps.

Full design details live in [docs/architecture.md](docs/architecture.md). The security model — what's protected, how, and what's tunable — lives in [docs/security.md](docs/security.md).

## Quick start (attendees)

Before you start, make sure you've done everything in [docs/prerequisites.md](docs/prerequisites.md) — a Google account with the $300 free trial activated (needs a card on file, do this the day before, not the morning of) and a model-provider API key ready to paste in when asked.

1. Open [shell.cloud.google.com](https://shell.cloud.google.com) and sign in with the Google account you set up billing with.
2. Run:
   ```
   curl -fsSL https://get.hermesanvil.dev | bash
   ```
3. Follow the on-screen wizard — it'll ask you to name your agent, walk through a couple of setup steps, and finish by "hatching" your VM. Takes about 15–20 minutes.
4. At the end, it writes a handoff file to your Cloud Shell home directory (`~/hermes-anvil-<your-agent>-handoff.md`) with your reconnect command and next steps — that file survives across Cloud Shell sessions, so you can always come back to it.

> **Note:** this is what the finished harness will feel like to use. The harness itself isn't built yet — see Status below.

## Quick start (developing the harness)

There's no application code yet (see Status). Once the `src/hermes_anvil` package exists, local iteration will run against `--dry-run` mode (fake MCP/SDK responses, $0 cost) rather than a real GCP project — see the "Testing without burning real GCP spend" section of [docs/architecture.md](docs/architecture.md).

## Status

Early scaffold. No application code yet — see `docs/` for the design this repo is being built against.

## Docs

- [docs/architecture.md](docs/architecture.md) — how the harness works end to end
- [docs/prerequisites.md](docs/prerequisites.md) — what attendees need before the workshop
- [docs/security.md](docs/security.md) — the security posture log
