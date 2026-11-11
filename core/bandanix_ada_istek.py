"""Pano ve not kısayolları için yerel ada isteği."""
from __future__ import annotations

import os
import socket
import stat
import tempfile
from pathlib import Path

PANELS = ("pano", "not")


def socket_path() -> Path:
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir())
    folder = runtime / f"bandanix-ada-{os.getuid()}"
    folder.mkdir(mode=0o700, exist_ok=True)
    info = folder.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise PermissionError(folder)
    return folder / "kontrol.sock"


def open_panel(panel: str) -> bool:
    if panel not in PANELS:
        return False
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(1.0)
            client.connect(str(socket_path()))
            client.sendall(panel.encode("ascii") + b"\n")
            with client.makefile("rb") as reply:
                return reply.readline(8) == b"ok\n"
    except OSError:
        return False
