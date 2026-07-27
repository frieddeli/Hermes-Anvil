# Developer guide

Everything a maintainer needs that isn't already covered by [architecture.md](architecture.md) (how it's built) or [security.md](security.md) (the security model). This doc tracks what's implemented, what's verified, and what to do next -- read it before touching the code or planning a real run.

## Current status

Implemented and fully tested in `--dry-run` mode: 23 tests passing, including a Textual pilot smoke test that drives all 12 screens end-to-end. Zero real GCP calls have ever been made -- everything below this line is what stands between "tests pass against fakes" and "works for real in Cloud Shell."

## Outstanding verification gaps (block a real run)

None of these have been tried against a live GCP project yet:

1. **Compute Engine MCP tool names are guessed, not verified.** `src/hermes_anvil/mcp/compute_server.py` uses `compute.instances.insert`/`compute.instances.get`, inferred from REST API naming conventions. Confirm against `https://compute.googleapis.com/mcp`'s real `list_tools()` output before relying on them.
2. **gcloud-mcp has never been run for real.** Unconfirmed: its actual tool schema, and whether its denylist permits `projects create` / `services enable` / `billing projects link` -- the exact calls `gcp/bootstrap.py` depends on.
3. **Hermes Agent's real CLI surface is assumed from a README read, not confirmed.** `gcp/startup_script.sh.j2` assumes `hermes gateway` is the right long-running command and `~/.hermes/config.yaml` is the right config path.

**Plan for closing these:** spin up a real GCP project/VM and test directly (in progress) -- that's the only way to convert these from "documented assumption" to "confirmed."

## Distribution gaps (block real users even once the above are fixed)

- **Hosting for the bootstrap one-liner: resolved.** Served directly off this repo via `raw.githubusercontent.com/frieddeli/Hermes-Anvil/main/scripts/bootstrap.sh` rather than a custom domain -- zero setup, already live now that the repo is pushed.
- **Not published to PyPI.** `scripts/bootstrap.sh` runs `uvx hermes-anvil`, which needs either a PyPI release or a `uvx --from git+https://...` fallback. Decide roughly a week before release based on remaining churn (see `docs/architecture.md`'s Distribution section).

## Dev environment setup

```
uv venv --python 3.11 && source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Running tests

```
python -m pytest
```

All 23 tests run against `dryrun/fakes.py` -- no `gcloud`, no real credentials, no cost. If you're adding a new `gcp/*.py` function, wire a corresponding fake into `FakeGcpToolRouter`/`FakeSecretWriter` rather than mocking at the test level, so `test_dryrun_flow.py` and `test_tui_smoke.py` keep exercising it too.

## Running the TUI locally

```
python -m hermes_anvil --dry-run
```

Launches the real Textual app through all 12 screens against fakes. Useful flags:

- `--dry-run` -- fake GCP/MCP backends, $0 cost, snappy polling intervals.
- `--resume SLUG` -- resume a previous run by its agent slug (reads `~/.hermes-anvil/<slug>.json`, or `~/.hermes-anvil/dry-run/<slug>.json` under `--dry-run`).
- `--allow-public-ip` -- pre-selects the public-IP option on the network screen (still requires the in-app typed risk acknowledgment; this flag never bypasses that).
- `--teardown SLUG` -- prints the `scripts/dev_teardown.sh` invocation for a given run.

There is currently no way to point this at a real GCP project and have it actually work end-to-end -- that's exactly gap #1-3 above.

## Testing against a real GCP project without burning unnecessary spend

- Use a personal/dev GCP project, kept separate from any real user's project.
- `scripts/dev_teardown.sh --slug <slug> --project <project-id> [--delete-project] [--yes]` deletes the VM/firewall rules/service account/secret (and optionally the whole project) after each dev iteration.
- Set a small budget alert (~$5) on the dev project to catch anything a failed teardown leaves behind.
- Do one full real run (non-`--dry-run`) early, specifically to calibrate the polling timeouts in `gcp/compute.py` (`wait_for_running`'s defaults are guesses at real install/boot timing, not measured).

## Code review history

The codebase has been through one fresh-eyes audit (bugs fixed: a project-ID truncation bug that broke the collision-retry loop for long agent names, an event-loop mismatch that leaked the MCP client's subprocess/session on exit, missing error handling on three screens, a resume path that silently skipped billing linkage, dead token-refresh code, and a non-retry-safe secret writer). See `git log` for the full detail in each fix's commit message rather than duplicating it here -- this section exists so a future audit knows one has already happened and roughly what it covered.

## Known non-goals for v1

- **Hermes managing its own VM via MCP** (deferred to v2 -- see `docs/architecture.md` and `docs/security.md`). Don't add this without deliberately revisiting that decision.
- **Pinning Hermes to a single terminal backend** and **unattended OS patching** are documented-but-not-enabled security measures (`docs/security.md`, measures 7 and 9) -- intentional, not oversights.
