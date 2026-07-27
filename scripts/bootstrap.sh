#!/usr/bin/env bash
set -euo pipefail

# --- styling (disabled automatically for non-terminal output or NO_COLOR) ---
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
    BOLD=$'\033[1m'; DIM=$'\033[2m'; RESET=$'\033[0m'
    AMBER=$'\033[1;33m'; CYAN=$'\033[0;36m'; GREEN=$'\033[0;32m'; RED=$'\033[0;31m'
else
    BOLD=""; DIM=""; RESET=""; AMBER=""; CYAN=""; GREEN=""; RED=""
fi

banner() {
    printf '%s' "${AMBER}"
    cat <<'ART'
        ________________
       /                \
  ____/   HERMES ANVIL   \____
  \__________________________/
           |        |
         __|________|__
        /______________\
ART
    printf '%s\n' "${RESET}"
}

step() { printf '%s[%s]%s %s\n' "${CYAN}" "$1" "${RESET}" "$2"; }
ok()   { printf '%s[ok]%s %s\n' "${GREEN}" "${RESET}" "$1"; }
fail() { printf '%s[fail]%s %s\n' "${RED}" "${RESET}" "$1" >&2; }

# Spinner runs while the given PID is alive; only animates on a real terminal.
spinner() {
    [ -t 1 ] || { wait "$1"; return $?; }
    local pid=$1 frames='|/-\' i=0
    while kill -0 "$pid" 2>/dev/null; do
        i=$(( (i + 1) % 4 ))
        printf '\r%s%s%s ' "${DIM}" "${frames:$i:1}" "${RESET}"
        sleep 0.1
    done
    printf '\r'
    wait "$pid"
}

banner
printf '%sHatch your own agent.%s\n\n' "${BOLD}" "${RESET}"

step "1/2" "Checking for uv..."
if ! command -v uv >/dev/null 2>&1; then
    printf '%suv not found, installing...%s\n' "${DIM}" "${RESET}"
    (curl -LsSf https://astral.sh/uv/install.sh | sh > /tmp/hermes-anvil-uv-install.log 2>&1) &
    install_pid=$!
    if spinner "$install_pid"; then
        ok "uv installed"
    else
        fail "uv install failed -- see /tmp/hermes-anvil-uv-install.log"
        exit 1
    fi

    if [ -f "$HOME/.local/bin/env" ]; then
        . "$HOME/.local/bin/env"
    elif [ -f "$HOME/.cargo/env" ]; then
        . "$HOME/.cargo/env"
    else
        export PATH="$HOME/.local/bin:$PATH"
    fi
else
    ok "uv is already installed"
fi

step "2/2" "Launching Hermes Anvil..."
printf '\n'
uvx --from git+https://github.com/frieddeli/Hermes-Anvil hermes-anvil
