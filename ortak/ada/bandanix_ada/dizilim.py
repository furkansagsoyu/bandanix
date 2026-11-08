"""Where each island is on screen, so islands can sit side by side.

Each island writes a tiny JSON file to $XDG_RUNTIME_DIR/bandanix/adalar/<name>.json
whenever it moves, grows or hides. No Qt here, so it is easy to test.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

GAP = 8


def folder() -> Path:
    base = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
    return Path(base) / "bandanix" / "adalar"


def publish(name: str, x: int, y: int, w: int, h: int, visible: bool) -> None:
    data = {"x": x, "y": y, "w": w, "h": h, "visible": bool(visible), "pid": os.getpid()}
    path = folder() / f"{name}.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        pass


def remove(name: str) -> None:
    try:
        (folder() / f"{name}.json").unlink()
    except OSError:
        pass


def _alive(pid) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read(name: str) -> dict | None:
    """The island's rectangle if it is running and visible, else None."""
    try:
        data = json.loads((folder() / f"{name}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not data.get("visible") or not _alive(data.get("pid")):
        return None
    if not all(isinstance(data.get(k), int) for k in ("x", "y", "w", "h")):
        return None
    return data


def place_beside(neighbour: dict | None, w: int, screen_x: int, screen_w: int,
                 top: int) -> tuple[int, int]:
    """Top-left corner for an island of width w: right of the neighbour, else centred."""
    if neighbour:
        x = neighbour["x"] + neighbour["w"] + GAP
        y = neighbour["y"]
    else:
        x = screen_x + (screen_w - w) // 2
        y = top
    return max(screen_x + GAP, min(x, screen_x + screen_w - w - GAP)), y
