"""Running things for the settings window: background steps with progress, and a terminal
window for installers that may ask for a password or a question."""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess

from gi.repository import Gio, GLib

from . import ortam


class Jobs:
    """One queue of background steps; reports progress to the window's status bar."""

    def __init__(self, on_progress, on_finish):
        self.on_progress = on_progress          # (fraction, text)
        self.on_finish = on_finish              # (ok, title, log)
        self.queue: list[tuple[str, list, list, object]] = []
        self.busy = False

    def run(self, title: str, steps: list[tuple[str, list[str]]], then=None) -> None:
        """steps: [(label, argv), ...]; run one after another, stop at the first failure.
        then(ok) runs after the last step (or the failure)."""
        self.queue.append((title, steps, [], then))
        if not self.busy:
            self._next_job()

    def _next_job(self) -> None:
        if not self.queue:
            self.busy = False
            return
        self.busy = True
        title, steps, log, _then = self.queue[0]
        self._step(title, steps, 0, log)

    def _step(self, title: str, steps: list, index: int, log: list) -> None:
        if index >= len(steps):
            self._done(True, title, log)
            return
        label, argv = steps[index]
        self.on_progress(index / len(steps), f"{title}: {label}")
        try:
            # stdin stays empty: installers then take their default answers instead of waiting
            proc = Gio.Subprocess.new(argv, Gio.SubprocessFlags.STDOUT_PIPE
                                      | Gio.SubprocessFlags.STDERR_MERGE)
        except GLib.Error as err:
            log.append(f"{label}: {err.message}")
            self._done(False, title, log)
            return

        def finished(p, result):
            try:
                _ok, out, _err = p.communicate_utf8_finish(result)
            except GLib.Error as err:
                out = err.message
            log.append(f"== {label}\n{out or ''}")
            if p.get_successful():
                self._step(title, steps, index + 1, log)
            else:
                self._done(False, title, log)

        proc.communicate_utf8_async(None, None, finished)

    def _done(self, ok: bool, title: str, log: list) -> None:
        _title, _steps, _log, then = self.queue.pop(0)
        self.on_progress(1.0, "")
        if then is not None:
            then(ok)
        self.on_finish(ok, title, "\n".join(log))
        self._next_job()


def terminal(command: str, on_exit=None) -> bool:
    """Run a shell command in a terminal window (the user can answer questions there)."""
    script = f"{command}; echo; read -rp 'Kapatmak için Enter tuşuna bas… ' _"
    if shutil.which("gnome-terminal"):
        argv = ["gnome-terminal", "--wait", "--title=Bandanix", "--", "bash", "-c", script]
    elif shutil.which("x-terminal-emulator"):
        argv = ["x-terminal-emulator", "-e", "bash", "-c", script]
    else:
        return False
    try:
        proc = Gio.Subprocess.new(argv, Gio.SubprocessFlags.NONE)
    except GLib.Error:
        return False
    if on_exit is not None:
        proc.wait_async(None, lambda p, r: on_exit())
    return True


def in_source(*args: str) -> str:
    src = ortam.source()
    return f"cd {shlex.quote(str(src))} && " + " ".join(shlex.quote(a) for a in args) if src else ""


def quick(argv: list[str], timeout: float = 20) -> tuple[bool, str]:
    """A short command whose answer is needed right away."""
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as err:
        return False, str(err)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def background(argv: list[str], on_done) -> None:
    """A command that may take a while (network); on_done(ok, output) on the main loop."""
    try:
        proc = Gio.Subprocess.new(argv, Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
    except GLib.Error as err:
        on_done(False, err.message)
        return

    def finished(p, result):
        try:
            _ok, out, _err = p.communicate_utf8_finish(result)
        except GLib.Error as err:
            on_done(False, err.message)
            return
        on_done(p.get_successful(), out or "")

    proc.communicate_utf8_async(None, None, finished)


def restart_sound_island() -> None:
    if not ortam.installed("sound-island"):
        return
    running = quick(["pgrep", "-f", "(^|/)python( -X faulthandler)? -m sound_island( |$)"])[0]
    subprocess.run(["pkill", "-f", "(^|/)python( -X faulthandler)? -m sound_island( |$)"], check=False)
    if running:
        launcher = ortam.BIN / "bandanix-ada"
        if not launcher.exists():
            launcher = ortam.BIN / "sound-island"
        GLib.timeout_add(600, lambda: subprocess.Popen(
            [str(launcher)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True) and False)


def cinnamon_osd(on: bool) -> None:
    """Our volume indicator on -> Cinnamon's own off (remembered for uninstall), and back."""
    yedek = str(ortam.BIN / "bandanix-yedek")
    if not os.access(yedek, os.X_OK):
        return
    if not quick(["gsettings", "writable", "org.cinnamon", "show-media-keys-osd"])[0]:
        return
    if on:
        quick([yedek, "isaretle", "sound-island", "dconf:/org/cinnamon/show-media-keys-osd"])
        kind = quick(["gsettings", "range", "org.cinnamon", "show-media-keys-osd"])[1]
        value = "false" if kind.startswith("type b") else "'disabled'"
        quick(["dconf", "write", "/org/cinnamon/show-media-keys-osd", value])
    else:
        quick([yedek, "geri-al", "sound-island"])
