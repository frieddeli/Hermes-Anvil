# Hermes Anvil

**Hatch your own agent.**

Hermes Anvil is a guided setup tool. Run one command in your browser, answer a few questions, and walk away owning a live, running [Hermes Agent](https://github.com/nousresearch/hermes-agent), a self-improving AI agent with persistent memory that keeps learning the more you use it. It's yours, living in your own Google Cloud project under your own billing, so you can keep using it for as long as you want.

No coding experience needed. If you can copy and paste a command, you can do this.

## Before you start

You'll need three things ready ahead of time:

1. **A Google account** with the GCP free trial activated ($300 in credit, usable for about 90 days). You'll need a card on file for verification, though you won't be charged during the trial.
2. **A model-provider API key** for your agent's "brain." We recommend [OpenRouter](https://openrouter.ai): it's free to start, no card needed, and a one-time $10 top-up (never expires) unlocks 1,000 free requests a day on their `:free` models. Nous Portal and OpenAI also work.
3. **Access to Google Cloud Shell**, which just needs a browser, nothing to install.

Full details, including exactly where to sign up and what to watch out for, are in [docs/prerequisites.md](docs/prerequisites.md). Please don't skip this: the setup tool can't do these steps for you, since Google requires a human to do them.

## Hatching your agent

1. Open [shell.cloud.google.com](https://shell.cloud.google.com) and sign in with the Google account you set up billing with.
2. Run:
   ```
   curl -fsSL https://raw.githubusercontent.com/frieddeli/Hermes-Anvil/main/scripts/bootstrap.sh | bash
   ```
3. Follow the on-screen wizard. It'll ask you to name your agent, then take care of everything else: setting up your project securely, storing your API key safely, and building your agent's new home. Takes about 15 to 20 minutes.
4. When it's done, you'll get a handoff file in your Cloud Shell home directory (`~/hermes-anvil-<your-agent>-handoff.md`) with everything you need to reconnect later. It's still there next time you open Cloud Shell, even after this session ends.

## What you get

A running AI agent, in a project only you control, that:

- Remembers things across conversations and improves its own skills over time.
- Is reachable securely from anywhere via `gcloud compute ssh`, with no open ports on the internet by default.
- Can be extended with more tools later, like Gmail or Calendar access; your handoff doc includes ready-to-use snippets for that.

See [docs/security.md](docs/security.md) for what's actually protecting your agent, and [docs/architecture.md](docs/architecture.md) if you want to know how the whole thing fits together.

## Something not working?

Check [docs/prerequisites.md](docs/prerequisites.md) first. Most snags come down to a missed prerequisite step: billing not active yet, or a card verification still pending. If you're stuck beyond that, [open an issue](../../issues).

## What this costs after your free trial ends

Your agent's VM is not covered by GCP's perpetual Always Free tier, which only covers a smaller `e2-micro` instance in specific US regions. This setup uses a bigger one. Once your $300 credit runs out or 90 days pass, whichever comes first, the VM starts billing to the card on your account, usually around $10 to 15 a month. Everything else (Secret Manager, IAM, the secure SSH tunnel) stays free or close to it regardless.

To keep running for free indefinitely instead, resize your VM down to an `e2-micro` instance in `us-west1`, `us-central1`, or `us-east1` before your credit runs out; this isn't done for you automatically. Either way, set a budget alert in the GCP Console so you get a heads-up before anything bills you. Your handoff doc repeats this note so it's there when you actually need it.

---

*Maintaining or extending Hermes Anvil itself? See [docs/dev-guide.md](docs/dev-guide.md).*
