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

# Everything that actually runs lives inside main(), invoked at the very
# bottom via `main "$@"` -- not just style. This script is meant to be run
# as `curl ... | bash`, which means bash reads its OWN script text
# progressively from stdin as it executes each line. If a bare top-level
# line further down did `exec < /dev/tty` (needed below, see why), every
# line bash had not yet read at that point -- including the final `uvx`
# launch -- would then also be read from the NEW stdin instead of the
# original piped stream, i.e. bash would sit there waiting for someone to
# type the rest of this script into the terminal by hand. Confirmed live:
# exactly this hang, reproduced and root-caused against a real piped
# invocation. Wrapping the whole body in one function sidesteps it --
# bash must fully parse a function's closing brace before it can execute
# any of it, so by the time main() actually runs, there's no unread
# script content left on the original stdin for the later redirect to
# collide with.
main() {
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

    # bash's own stdin (fd 0) is the pipe FROM curl when run as
    # `curl ... | bash`, not the user's real terminal. Every subprocess
    # bash launches inherits that same fd 0 by default, including the TUI
    # below. By the time curl has finished streaming the script, that pipe
    # is exhausted, so the TUI would inherit an already-EOF'd, non-tty
    # stdin -- it can never read a keystroke, no matter what's wrong (or
    # not wrong) with its own input handling. Confirmed live: the
    # identical `uvx --refresh ...` command run directly in an interactive
    # shell works fine; only the piped invocation hangs with an
    # unresponsive terminal. Reattaching stdin to the controlling terminal
    # before launching fixes it -- safe here specifically because main()
    # (see above) guarantees bash has nothing left to read from the old
    # stdin by this point. Guarded by `[ -t 0 ]` so this is a no-op when
    # the script is run normally (not piped), where stdin is already the
    # real terminal.
    if [ ! -t 0 ]; then
        exec < /dev/tty
    fi

    # --refresh is required, not optional: confirmed live that a plain
    # `uvx --from git+URL` can serve a stale cached build instead of
    # re-resolving the latest commit on the branch. Without this, a real
    # attendee running this exact script has no way to know they're on old
    # code -- the app just silently runs whatever uv happened to have
    # cached from a previous invocation of the same URL, which could be
    # anyone's, any time in the past.
    uvx --refresh --from git+https://github.com/frieddeli/Hermes-Anvil hermes-anvil
}

main "$@"
