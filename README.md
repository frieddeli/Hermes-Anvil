# Hermes Anvil

**Hatch your own agent.**

Hermes Anvil is a guided setup tool for the workshop. Run one command in your browser, answer a few questions, and walk away owning a live, running [Hermes Agent](https://github.com/nousresearch/hermes-agent) — a self-improving AI agent with persistent memory that keeps learning the more you use it. It's yours: it lives in your own Google Cloud project, under your own billing, and you can keep using it long after the workshop ends.

No coding experience needed. If you can copy and paste a command, you can do this.

## Before you start

You'll need three things ready ahead of time — **do this at least a day before the workshop**, not the morning of:

1. **A Google account** with the GCP free trial activated ($300 in credit, usable for about 90 days — needs a card on file for verification, though you won't be charged during the trial).
2. **A model-provider API key** for your agent's "brain" — we recommend [OpenRouter](https://openrouter.ai): it's free to start (no card needed), and a one-time $10 top-up (never expires) unlocks 1,000 free requests a day on their `:free` models. Nous Portal and OpenAI also work.
3. **Access to Google Cloud Shell** — just needs a browser, nothing to install.

Full details, including exactly where to sign up and what to watch out for, are in [docs/prerequisites.md](docs/prerequisites.md). Please don't skip this — the setup tool can't do these steps for you, since Google requires a human to do them.

## Hatching your agent

1. Open [shell.cloud.google.com](https://shell.cloud.google.com) and sign in with the Google account you set up billing with.
2. Run:
   ```
   curl -fsSL https://raw.githubusercontent.com/<org>/hermes-anvil/main/scripts/bootstrap.sh | bash
   ```
3. Follow the on-screen wizard. It'll ask you to name your agent, then take care of everything else — setting up your project securely, storing your API key safely, and building your agent's new home. Takes about 15–20 minutes.
4. When it's done, you'll get a handoff file in your Cloud Shell home directory (`~/hermes-anvil-<your-agent>-handoff.md`) with everything you need to reconnect later — it's still there next time you open Cloud Shell, even after this session ends.

## What you get

A running AI agent, in a project only you control, that:

- Remembers things across conversations and improves its own skills over time.
- Is reachable securely from anywhere via `gcloud compute ssh` — no open ports on the internet by default.
- Can be extended with more tools later (like Gmail or Calendar access) — your handoff doc includes ready-to-use snippets for that.

Curious what's actually protecting your agent, or how the whole thing fits together under the hood? See [docs/security.md](docs/security.md) and [docs/architecture.md](docs/architecture.md).

## Something not working?

Check [docs/prerequisites.md](docs/prerequisites.md) first — most snags are a missed prerequisite step (billing not active yet, or a card verification still pending). If you're stuck beyond that, flag a workshop organizer.

---

*Maintaining or extending Hermes Anvil itself? See [docs/dev-guide.md](docs/dev-guide.md).*
