"""Clipboard watcher: wakes up only when the clipboard changes and stores new text.

Copies that a password manager marks as secret are never stored.
"""
from __future__ import annotations

import fcntl
import os
import signal
import sys
import tempfile
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

import pano_gecmis as pano  # noqa: E402

RUN = Path(os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()) / "bandanix"


class Watcher:
    def __init__(self):
        self.busy = False
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.clipboard.connect("owner-change", self.on_change)

    def on_change(self, clipboard, _event) -> None:
        if self.busy:
            return
        # read a moment later: some apps announce the change before the data is ready
        GLib.timeout_add(80, self.read)

    def read(self) -> bool:
        if self.busy:
            return False
        self.busy = True
        try:
            ok, atoms = self.clipboard.wait_for_targets()
            targets = [a.name() for a in atoms] if ok and atoms else []
            if pano.PASSWORD_HINT in targets:
                return False
            text = self.clipboard.wait_for_text()
            if pano.acceptable(text, targets):
                pano.add(text, time.time())
        except Exception as err:            # never let one odd copy stop the watcher
            print(f"bandanix-pano: {err}", file=sys.stderr)
        finally:
            self.busy = False
        return False


def run() -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    lock = open(RUN / "pano-bekci.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return 0                          # already running
    lock.write(str(os.getpid()))
    lock.flush()
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, Gtk.main_quit)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, Gtk.main_quit)
    Watcher()
    Gtk.main()
    return 0
