"""Live-tail helper for the subprocess log file (see mcp/client.py), so a
screen doing GCP work can show real activity instead of a static status
line sitting still for however long a subprocess takes to start.

Redirecting subprocess stderr straight to a log file fixed the log lines
rendering over the TUI, but left a real UX gap: a long silent wait during
e.g. gcloud-mcp's first `npx` package fetch is visually indistinguishable
from a genuine hang -- which is exactly what made earlier debugging of a
real hang report so hard to pin down.

An earlier version tried to tee stdio_client()'s `errlog` writes into an
in-process queue via a custom file-like wrapper. That broke: `errlog` is
handed to the subprocess machinery as a raw OS-level stderr target, which
requires a real `fileno()` -- child-process writes happen at the fd level
and never go through a Python object's `write()` at all. Tailing the log
file itself sidesteps that entirely: it doesn't care how the bytes got
there.
"""

from __future__ import annotations

from pathlib import Path

_tail_positions: dict[Path, int] = {}


def poll_file(path: Path) -> list[str]:
    """Return any complete lines appended to `path` since the last call.

    Non-blocking, safe to call on a timer even before the file exists.
    """
    try:
        with path.open("r") as f:
            f.seek(_tail_positions.get(path, 0))
            data = f.read()
            _tail_positions[path] = f.tell()
    except FileNotFoundError:
        return []
    return [line for line in data.splitlines() if line.strip()]
