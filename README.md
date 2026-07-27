
# Hermes Anvil

A guided deployment harness for a "hatch your own agent" workshop. Each attendee runs one command in Google Cloud Shell and comes out the other side owning a live, running instance of [Hermes Agent](https://github.com/nousresearch/hermes-agent) in their own GCP project — theirs to keep and take home.

## What this is

Hermes Anvil is the harness, not the agent. It's an interactive terminal wizard (TUI) that an attendee runs in Cloud Shell, which:

1. Verifies they already have GCP billing enabled (a pre-workshop prerequisite — see [docs/prerequisites.md](docs/prerequisites.md)).
2. Creates their GCP project, enables the required APIs, and sets up a least-privilege service account, network rules, and a Secret Manager entry for their model-provider API key.
3. Provisions a small VM and installs Hermes Agent on it.
4. Hands off a connection guide and next steps.

Full design details live in [docs/architecture.md](docs/architecture.md). The security model — what's protected, how, and what's tunable — lives in [docs/security.md](docs/security.md).

## Quick start (attendees) — not usable yet, see Status

This is the intended end-state UX, once the items in Status below are done:

1. Open [shell.cloud.google.com](https://shell.cloud.google.com) and sign in with the Google account you set up billing with.
2. Run:
   ```
   curl -fsSL https://get.hermesanvil.dev | bash
   ```
3. Follow the on-screen wizard — it'll ask you to name your agent, walk through a couple of setup steps, and finish by "hatching" your VM. Takes about 15–20 minutes.
4. At the end, it writes a handoff file to your Cloud Shell home directory (`~/hermes-anvil-<your-agent>-handoff.md`) with your reconnect command and next steps.

**This does not work today.** `get.hermesanvil.dev` isn't hosted, and nothing is published to PyPI yet, so step 2 has nothing to install. Don't try this in Cloud Shell until Status below says otherwise.

## Quick start (developing/testing right now)

The application code exists and passes its full test suite (`--dry-run` mode, zero real GCP calls), but has never been run against a real GCP project. To try it yourself today, from a clone of this repo:

```
uv venv --python 3.11 && source .venv/bin/activate
uv pip install -e ".[dev]"
python -m pytest              # 23 tests, all against fakes -- $0 cost
python -m hermes_anvil --dry-run
```

The last command launches the real TUI, walking through all 12 screens end-to-end, but every GCP/MCP call is faked (see `dryrun/fakes.py`) -- nothing touches real Google Cloud. There is no way yet to point this at a real GCP project (no `gcloud`/MCP tool-name verification has been done -- see Status).

## Status

Implemented and tested in `--dry-run` only. Before this can run for real in Cloud Shell, three things need to happen against an actual GCP project (none have been tried yet):

1. **Verify the Compute Engine MCP server's real tool names.** `mcp/compute_server.py` guesses `compute.instances.insert`/`compute.instances.get` from REST API naming conventions — never confirmed against a live `https://compute.googleapis.com/mcp` via `list_tools()`.
2. **Verify gcloud-mcp actually works as assumed.** Never run `npx @google-cloud/gcloud-mcp` for real — its tool schema and whether its denylist blocks `projects create`/`services enable`/`billing projects link` are unconfirmed.
3. **Verify Hermes Agent's real CLI surface.** The startup script assumes `hermes gateway` is the right long-running command and `~/.hermes/config.yaml` is the right config path, based on a README read, not an actual install.

Separately, before an attendee could use it: publish to PyPI (or point `bootstrap.sh` at a git ref) and stand up hosting for the `curl` URL. Neither is set up.

## Docs

- [docs/architecture.md](docs/architecture.md) — how the harness works end to end
- [docs/prerequisites.md](docs/prerequisites.md) — what attendees need before the workshop
- [docs/security.md](docs/security.md) — the security posture log
