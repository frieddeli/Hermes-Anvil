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

1. **Compute Engine MCP tool names: conflicting research, still unresolved.** `src/hermes_anvil/mcp/compute_server.py` uses `compute.instances.insert`/`compute.instances.get`. Two independent research passes gave contradictory answers: a direct WebFetch of `docs.cloud.google.com/compute/docs/use-compute-engine-mcp` found no explicit tool-name list on that page at all; a separate pass (agy/Antigravity CLI) claimed to find a "MCP tools reference" section there listing snake_case names instead (`create_instance`, `get_instance_basic_info`, `delete_instance`, `start_instance`, `stop_instance`, `reset_instance`, `list_instances`, `set_instance_machine_type`, `list_instance_attached_disks`). **Do not adopt either version on faith** -- this needs the actual `list_tools()` call against the live server with real credentials, which is exactly the real-GCP-test step already planned. If those snake_case names turn out to be real, they're a strong lead; if not, don't let a single unverified source overwrite working code.
2. **gcloud-mcp has never been run for real.** Confirmed to exist on npm (`npm view @google-cloud/gcloud-mcp` → real package, v0.5.3), but its actual tool schema, and whether its denylist permits `projects create` / `services enable` / `billing projects link` -- the exact calls `gcp/bootstrap.py` depends on -- remain unconfirmed.
3. **Hermes Agent's CLI surface: mostly confirmed now, one real gap found and fixed, one known limitation remains.** A second research pass against Hermes's actual docs (not just the README) resolved most of this:
   - `hermes gateway` (foreground) is a real, confirmed invocation -- `hermes gateway setup` is a separate, *optional* step only needed for connecting messaging platforms (Telegram/Discord/etc.), which this project doesn't use. The original invocation was fine.
   - `~/.hermes/config.yaml` is confirmed real for general config (`agent_name` etc.).
   - **Real bug found and fixed:** the API key was being written into `config.yaml` under `model_provider: api_key:` -- wrong mechanism. The real one, confirmed against Hermes's docs, is `hermes config set OPENROUTER_API_KEY <value>`, which routes to `~/.hermes/.env`. `startup_script.sh.j2` now uses this.
   - **Real bug found and fixed:** the installer requires `source ~/.bashrc` per its own quickstart docs to put `hermes` on PATH, but systemd doesn't source `.bashrc` -- the old `ExecStart=... hermes gateway` would likely have failed with "command not found" on first boot. The script now resolves the real binary path explicitly (`command -v hermes` under a login shell) and uses the full path, failing loudly at provision time if it's not found rather than silently at service-start time.
   - **Known remaining gap:** `hermes config set OPENROUTER_API_KEY` assumes the attendee used OpenRouter (this project's recommended default). The harness doesn't currently ask which provider was actually used, so Nous Portal or OpenAI users would get the wrong key name written. Not fixed -- would need a provider-selection step added to `secret_setup.py` and threaded through to the startup script.
4. **OpenShell's policy schema was fixed after being found wrong -- and it changed the security design.** The original policy (`filesystem`/`landlock.mode`/a simple `network: {default: allow, deny: [...]}` block) was checked against OpenShell's real docs (`docs.nvidia.com/openshell/sandboxes/policies`) and found structurally incorrect: the real top-level keys are `filesystem_policy` (with `read_only`/`read_write` path lists, not per-entry allow/deny), `landlock.compatibility` (not `landlock.mode`), and `process` (for `run_as_user`/`run_as_group`). More importantly, OpenShell's real network model (`network_policies`) is a per-endpoint-and-binary allowlist that denies anything unmatched by default -- the opposite of this project's permissive-by-default network stance, which exists specifically so Hermes can reach arbitrary MCP servers/APIs a user adds later. Rather than force-fit a mismatched model, the fix moves the one network-layer control this project actually needs (blocking the GCP metadata server) out of OpenShell entirely, into a plain `iptables` rule scoped to the `hermes` user's UID -- see `docs/security.md` measures 5 and 6. OpenShell's role is now filesystem + process isolation only.

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

## Known non-goals for v1

- **Hermes managing its own VM via MCP** (deferred to v2 -- see `docs/architecture.md` and `docs/security.md`). Don't add this without deliberately revisiting that decision.
- **Pinning Hermes to a single terminal backend** and **unattended OS patching** are documented-but-not-enabled security measures (`docs/security.md`, measures 7 and 9) -- intentional, not oversights.
