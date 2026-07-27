# Notes for Claude Code working in this repo

## This is a public repository

`github.com/frieddeli/Hermes-Anvil` is public. Before every commit and especially before every push:

- Review the actual diff (`git diff --staged`), not just the file list -- don't `git add -A` and trust it blindly.
- Never commit real credentials, API keys, or service-account JSON. `.gitignore` already has defensive patterns for common cases (`.env`, `*-key.json`, `*credentials*.json`, etc.), but that's a backstop, not a substitute for looking.
- Be careful with personal information in commit *metadata*, not just file content -- `git log -p` shows author name/email, which a plain content grep won't catch. This already happened once: the repo was pushed with the owner's real Gmail in every commit's author field before anyone checked; had to rewrite history and force-push to fix it, which is only safe because nothing had been pulled yet. Don't rely on that safety margin existing next time.
- Local-only dev tooling (the `pixi`-based test environment for real `gcloud` CLI access, any future `.claude/` project config) is gitignored on purpose -- keep it that way, don't `git add -f` it in.

## Local test environment

A pixi-based environment with the real `gcloud` CLI lives outside this repo, in the scratchpad directory, specifically because pixi's generated launcher scripts break when the install path contains a space (this repo's own directory name, "Hermes Anvil", has one) -- Google's own `gcloud` launcher does an unquoted `export CLOUDSDK_PYTHON=<path>`, which breaks on the space. Don't recreate a pixi environment inside this repo's own directory; it will hit the same bug.
