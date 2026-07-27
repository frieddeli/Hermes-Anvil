frieddeli@cloudshell:~ (project-568833c4-02c4-45cd-a06)$Your Cloud Platform project in this session is set to project-568833c4-02c4-45cd-a06.

Use `gcloud config set project [PROJECT_ID]` to change to a different project.

frieddeli@cloudshell:~ (project-568833c4-02c4-45cd-a06)$ curl -fsSL https://raw.githubusercontent.com/frieddeli/Hermes-Anvil/main/scripts/bootstrap.sh | bash

Checking for uv...

uv is already installed.

Launching Hermes Anvil...

  × No solution found when resolving tool dependencies:

  ╰─▶ Because hermes-anvil was not found in the package registry and you require hermes-anvil, we can conclude that your requirements are unsatisfiable.

frieddeli@cloudshell:~ (project-568833c4-02c4-45cd-a06)$Your Cloud Platform project in this session is set to project-568833c4-02c4-45cd-a06.

frieddeli@cloudshell:~ (project-568833c4-02c4-45cd-a06)$

# Developer guide

Everything a maintainer needs that isn't already covered by [architecture.md](architecture.md) (how it's built) or [security.md](security.md) (the security model). This doc tracks what's implemented, what's verified, and what to do next -- read it before touching the code or planning a real run.

## Current status

Implemented and fully tested in `--dry-run` mode: 23 tests passing, including a Textual pilot smoke test that drives all 12 screens end-to-end. Zero real GCP calls have ever been made -- everything below this line is what stands between "tests pass against fakes" and "works for real in Cloud Shell."

## Outstanding verification gaps (block a real run)

1. **Compute Engine MCP tool names: conflicting research, still unresolved -- and now a concrete reason to distrust the guess more.** `src/hermes_anvil/mcp/compute_server.py` uses `compute.instances.insert`/`compute.instances.get`. Two independent research passes gave contradictory answers (see prior note below for detail). Gap #2 below found that gcloud-mcp's real input schema differed from what was guessed for it -- a sibling MCP server, same class of assumption, proven wrong. Treat the Compute Engine MCP tool names AND the request body shape (`instanceResource`, `machineType`, etc.) as equally likely to need correction. Still needs the actual `list_tools()` call against the live server with real credentials.
2. **gcloud-mcp: now verified working end to end, one real bug found and fixed.** Set up a local pixi environment with the real `gcloud` CLI specifically to test this for real (previously only checked that the npm package exists). Confirmed: the server starts and connects successfully in ~1-2s, `run_gcloud_command` is the correct tool name. **Real bug found and fixed:** its actual input schema is `{"args": [...]}` (a list), not `{"command": "..."}` (a joined string) -- the latter was the original guess and fails MCP input validation on every call. A real `gcloud auth list` call now succeeds end to end through the production `GcloudMcpServer` code path. Still unconfirmed: whether the denylist permits `projects create` / `services enable` / `billing projects link` specifically.
3. **Real bug found and fixed: `McpClient`'s connect methods had no protection against hanging, and the first fix attempt was itself broken.** Triggered by an actual Cloud Shell report -- "press enter, nothing happens." Root-caused by testing against a real running gcloud-mcp process (not just reasoning about it): wrapping `connect_stdio`'s `AsyncExitStack`-based connect logic in `anyio.fail_after()` broke the connection with an anyio cancel-scope error EVEN ON THE SUCCESS PATH. Moving the timeout to the caller boundary with plain `asyncio.wait_for()` around `connect_stdio()` itself *also* broke, but differently: it corrupted a later, separate `close()` call, because `asyncio.wait_for()` runs its argument in a transient task, and the long-lived resources entered inside stay bound to that now-gone task. The fix that actually verified clean end to end (connect, real tool call, close, all via the real `GcloudMcpServer`): **no timeout around `connect()`** (bare `AsyncExitStack`, proven safe), **`asyncio.wait_for()` only around `call_tool()`** (doesn't create new long-lived resources, proven safe). This means: a hang during an actual tool call now fails loudly after `CALL_TIMEOUT_SECONDS`; a hang during the initial `npx` spawn/connect is still theoretically possible and unprotected -- lower risk now that connect is confirmed to normally take ~1-2s, but not eliminated.
4. **Hermes Agent's CLI surface: mostly confirmed now, one real gap found and fixed, one known limitation remains.** A second research pass against Hermes's actual docs (not just the README) resolved most of this:
   - `hermes gateway` (foreground) is a real, confirmed invocation -- `hermes gateway setup` is a separate, *optional* step only needed for connecting messaging platforms (Telegram/Discord/etc.), which this project doesn't use. The original invocation was fine.
   - `~/.hermes/config.yaml` is confirmed real for general config (`agent_name` etc.).
   - **Real bug found and fixed:** the API key was being written into `config.yaml` under `model_provider: api_key:` -- wrong mechanism. The real one, confirmed against Hermes's docs, is `hermes config set OPENROUTER_API_KEY <value>`, which routes to `~/.hermes/.env`. `startup_script.sh.j2` now uses this.
   - **Real bug found and fixed:** the installer requires `source ~/.bashrc` per its own quickstart docs to put `hermes` on PATH, but systemd doesn't source `.bashrc` -- the old `ExecStart=... hermes gateway` would likely have failed with "command not found" on first boot. The script now resolves the real binary path explicitly (`command -v hermes` under a login shell) and uses the full path, failing loudly at provision time if it's not found rather than silently at service-start time.
   - **Known remaining gap:** `hermes config set OPENROUTER_API_KEY` assumes the attendee used OpenRouter (this project's recommended default). The harness doesn't currently ask which provider was actually used, so Nous Portal or OpenAI users would get the wrong key name written. Not fixed -- would need a provider-selection step added to `secret_setup.py` and threaded through to the startup script.
5. **OpenShell's policy schema was fixed after being found wrong -- and it changed the security design.** The original policy (`filesystem`/`landlock.mode`/a simple `network: {default: allow, deny: [...]}` block) was checked against OpenShell's real docs (`docs.nvidia.com/openshell/sandboxes/policies`) and found structurally incorrect: the real top-level keys are `filesystem_policy` (with `read_only`/`read_write` path lists, not per-entry allow/deny), `landlock.compatibility` (not `landlock.mode`), and `process` (for `run_as_user`/`run_as_group`). More importantly, OpenShell's real network model (`network_policies`) is a per-endpoint-and-binary allowlist that denies anything unmatched by default -- the opposite of this project's permissive-by-default network stance, which exists specifically so Hermes can reach arbitrary MCP servers/APIs a user adds later. Rather than force-fit a mismatched model, the fix moves the one network-layer control this project actually needs (blocking the GCP metadata server) out of OpenShell entirely, into a plain `iptables` rule scoped to the `hermes` user's UID -- see `docs/security.md` measures 5 and 6. OpenShell's role is now filesystem + process isolation only.
6. **Real bug found and fixed: the startup script wasn't safe against reboots.** GCP re-runs an instance's `startup-script` metadata on *every* boot, not just at creation -- this wasn't accounted for. The old script would silently re-install Hermes and overwrite `config.yaml` (destroying any customization, like uncommenting the Workspace MCP block) on every reboot, and its only "already done" sentinel lived on tmpfs (`/run/...`), which is wiped every boot by definition, so it could never actually have prevented that. Fixed with a persistent marker (`/var/lib/hermes-anvil-provisioned`) checked at the very top of the script -- if present, the script exits immediately and leaves the already-running systemd-managed service alone.
7. **Real bug found and fixed: an unguarded `iptables` call could have taken down the entire provisioning, not just the metadata block.** Recent Debian images increasingly default to nftables-only, and `iptables`'s presence on the `debian-12` image was never actually verified. Under `set -euo pipefail`, a missing command there would abort the whole script -- OpenShell setup and the systemd unit that actually starts Hermes are defined *after* that line, so they'd never run either. Now guarded with `command -v iptables`, non-fatal if missing (same pattern already used for the OpenShell install step).
8. **Real bug found and fixed (from an actual Cloud Shell screenshot, not research): Textual's mouse-tracking escape sequences leak through as visible garbage text** (`^[[<0;137;14M` etc.) in Cloud Shell's web-based terminal, which doesn't cleanly consume SGR mouse reporting. Fixed by passing `mouse=False` to `run_async()` in `cli.py` (confirmed against the installed Textual source that this parameter exists). The app is fully keyboard-navigable, so nothing is lost.
9. **Real bug found and fixed, second Cloud Shell report: welcome screen renders cleanly (mouse fix confirmed working) but Enter does nothing, even after a forced fresh pull.** Diagnosed by process of elimination -- Ctrl+C still killed the process (alive, not deadlocked), ruling out a hang, which pointed at something terminal-protocol-specific rather than app logic. Confirmed by reading the installed Textual source directly: `textual/drivers/linux_driver.py` unconditionally writes a raw Kitty keyboard protocol activation sequence (`\x1b[>{flags}u`) at startup unless `TEXTUAL_DISABLE_KITTY_KEY` is set. xterm.js (which Cloud Shell's web terminal uses) has documented gaps handling that protocol, dropping keys like Enter and Backspace while others (letters, arrows, space) keep working -- matches the symptom exactly. Fixed in `cli.py` by setting `os.environ.setdefault("TEXTUAL_DISABLE_KITTY_KEY", "1")` before any Textual import; verified directly that this flips `textual.constants.DISABLE_KITTY_KEY` to `True` before the driver runs.

**Plan for closing the remaining ones:** spin up a real GCP project/VM and test directly (in progress) -- that's the only way to convert #1 and #2 from "documented assumption" to "confirmed."

## Distribution gaps (block real users even once the above are fixed)

- **Hosting for the bootstrap one-liner: resolved.** Served directly off this repo via `raw.githubusercontent.com/frieddeli/Hermes-Anvil/main/scripts/bootstrap.sh` rather than a custom domain -- zero setup, already live now that the repo is pushed.
- **PyPI vs. git+https: resolved.** `scripts/bootstrap.sh` runs `uvx --from git+https://github.com/frieddeli/Hermes-Anvil hermes-anvil`. This was forced by an actual failure: a plain `uvx hermes-anvil` was tried first in a real Cloud Shell session (2026-07-27) and failed with "hermes-anvil was not found in the package registry," since nothing's published to PyPI. Confirmed working after switching to the git+https form. A PyPI release is still possible later but isn't blocking anything now.

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

Two rounds so far. See `git log` for full detail in each fix's commit message rather than duplicating it here -- this section exists so a future audit knows what's already been covered.

- **Round 1, fresh-eyes code audit:** a project-ID truncation bug that broke the collision-retry loop for long agent names, an event-loop mismatch that leaked the MCP client's subprocess/session on exit, missing error handling on three screens, a resume path that silently skipped billing linkage, dead token-refresh code, and a non-retry-safe secret writer.
- **Round 2, triggered by a real Cloud Shell run failing on the PyPI issue (see Distribution gaps, resolved):** prompted an exhaustive external-reference sweep of every URL/package the codebase assumes exists. Found and fixed: the Google Workspace MCP URL was a single guessed endpoint that 404'd (real answer: no unified endpoint exists, each product has its own, e.g. `gmailmcp.googleapis.com`), the Hermes secret-injection and PATH issues described above, and the OpenShell policy schema issue described above. Everything else checked (astral.sh, GitHub URLs, `hermes-agent.nousresearch.com/install.sh`, `api.ipify.org`, the `@google-cloud/gcloud-mcp` npm package, GCP resource path conventions in `compute.py`) came back confirmed working.
- **Round 3, a fresh independent pass specifically hunting for anything not already tracked:** found and fixed the reboot-safety bug and the unguarded `iptables` call described above (gaps 5 and 6) -- both real, neither caught by rounds 1 or 2. Confirmed clean on a fresh re-read: `gcp/bootstrap.py`, `identity.py`, `network.py`, `secrets.py`, `state.py`, `naming.py`, `preflight.py`, the `mcp/` client layer, `cli.py`'s event-loop handling, `pyproject.toml`'s dependency/entry-point consistency, and `tests/test_dryrun_flow.py`'s assertion strength. Separately, an actual Cloud Shell screenshot from a real run surfaced gap 7 (the mouse-tracking garbage-text issue) -- something no amount of code review would have caught, only running it for real did.

## Known non-goals for v1

- **Hermes managing its own VM via MCP** (deferred to v2 -- see `docs/architecture.md` and `docs/security.md`). Don't add this without deliberately revisiting that decision.
- **Pinning Hermes to a single terminal backend** and **unattended OS patching** are documented-but-not-enabled security measures (`docs/security.md`, measures 7 and 9) -- intentional, not oversights.
