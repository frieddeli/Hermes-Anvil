#!/usr/bin/env bash
set -euo pipefail

echo "Checking for uv..."
if ! command -v uv >/dev/null 2>&1; then
    echo "uv not found. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    echo "Sourcing uv environment..."
    if [ -f "$HOME/.local/bin/env" ]; then
        . "$HOME/.local/bin/env"
    elif [ -f "$HOME/.cargo/env" ]; then
        . "$HOME/.cargo/env"
    else
        export PATH="$HOME/.local/bin:$PATH"
    fi
else
    echo "uv is already installed."
fi

echo "Launching Hermes Anvil..."
uvx --from git+https://github.com/frieddeli/Hermes-Anvil hermes-anvil
