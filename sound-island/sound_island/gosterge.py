"""Listens for volume and screen brightness changes, for the island's level indicator.

Both are event driven: `pactl subscribe` reports audio changes, `gdbus monitor` reports
the Cinnamon power daemon's brightness property. Nothing runs while nothing changes.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from .parsing import (backlight_percent, is_screen_changed, is_volume_event, parse_brightness,
                      parse_volume)

# LC_ALL=C: pactl translates its output, the parsers expect the English words
VOLUME_QUERY = "export LC_ALL=C; pactl get-sink-volume @DEFAULT_SINK@; pactl get-sink-mute @DEFAULT_SINK@"
BACKLIGHT = Path("/sys/class/backlight")
BACKLIGHT_ORDER = {"firmware": 0, "platform": 1, "raw": 2}     # same preference as the desktop
BRIGHTNESS_MONITOR = ["monitor", "--session", "--dest", "org.cinnamon.SettingsDaemon.Power",
                      "--object-path", "/org/cinnamon/SettingsDaemon/Power"]


class Levels(QObject):
    volume_changed = Signal(int, bool)
    changed = Signal(str, int, bool)     # "ses" | "parlaklik", percent, muted

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._stopping = False
        self._volume: tuple[int, bool] | None = None   # baseline: first reading is not shown
        self._backlight = self._find_backlight()
        self._brightness = self._read_backlight()
        self._pending = False
        self._buf = {"pactl": b"", "gdbus": b""}

        self._events = QProcess(self)
        self._events.readyReadStandardOutput.connect(self._read_events)
        self._events.finished.connect(lambda *_: self._restart(self._start_events))

        self._query = QProcess(self)
        self._query.finished.connect(self._read_query)

        self._control = QProcess(self)
        self._control.finished.connect(lambda *_: self._ask_volume())
        self._control.setStandardErrorFile(QProcess.nullDevice())
        self._monitor = QProcess(self)
        self._monitor.readyReadStandardOutput.connect(self._read_monitor)
        self._monitor.finished.connect(lambda *_: self._restart(self._start_monitor, 10000))

    # ---- lifecycle -----------------------------------------------------------------
    def start(self, *, monitor_brightness: bool = True) -> None:
        if shutil.which("pactl"):
            self._start_events()
            self._ask_volume()
        if monitor_brightness and shutil.which("gdbus"):
            self._start_monitor()

    def stop(self) -> None:
        self._stopping = True
        for proc in (self._events, self._query, self._control, self._monitor):
            if proc.state() != QProcess.ProcessState.NotRunning:
                proc.kill()
                proc.waitForFinished(500)

    def _restart(self, starter, ms: int = 2000) -> None:
        if not self._stopping:
            QTimer.singleShot(ms, starter)

    def _start_events(self) -> None:
        if self._stopping or self._events.state() != QProcess.ProcessState.NotRunning:
            return
        self._buf["pactl"] = b""
        self._events.start("env", ["LC_ALL=C", "pactl", "subscribe"])

    def _start_monitor(self) -> None:
        if self._stopping or self._monitor.state() != QProcess.ProcessState.NotRunning:
            return
        self._buf["gdbus"] = b""
        self._monitor.start("gdbus", BRIGHTNESS_MONITOR)

    # ---- volume ----------------------------------------------------------------------
    def _lines(self, key: str, proc: QProcess) -> list[str]:
        self._buf[key] += bytes(proc.readAllStandardOutput())
        *lines, self._buf[key] = self._buf[key].split(b"\n")
        return [line.decode("utf-8", "replace") for line in lines]

    def _read_events(self) -> None:
        if any(is_volume_event(line) for line in self._lines("pactl", self._events)):
            self._ask_volume()

    def adjust_volume(self, change: str) -> None:
        if self._control.state() != QProcess.ProcessState.NotRunning:
            return
        if change == "mute":
            args = ["set-sink-mute", "@DEFAULT_SINK@", "toggle"]
        elif self._volume is not None:
            value = min(100, max(0, self._volume[0] + (5 if change == "up" else -5)))
            args = ["set-sink-volume", "@DEFAULT_SINK@", f"{value}%"]
        else:
            return
        self._control.start("pactl", args)

    def _ask_volume(self) -> None:
        if self._stopping:
            return
        if self._query.state() != QProcess.ProcessState.NotRunning:
            self._pending = True               # one more read once this one is done
            return
        self._query.start("sh", ["-c", VOLUME_QUERY])

    def _read_query(self, *_) -> None:
        text = bytes(self._query.readAllStandardOutput()).decode("utf-8", "replace")
        reading = parse_volume(text)
        if reading is not None:
            previous = self._volume
            self._volume = reading
            if reading != previous:
                self.volume_changed.emit(*reading)
                if previous is not None:
                    self.changed.emit("ses", *reading)
        if self._pending:
            self._pending = False
            QTimer.singleShot(0, self._ask_volume)

    # ---- brightness ----------------------------------------------------------------
    @staticmethod
    def _find_backlight() -> Path | None:
        try:
            dirs = [d for d in BACKLIGHT.iterdir() if (d / "brightness").is_file()]
        except OSError:
            return None
        def rank(d: Path) -> int:
            try:
                return BACKLIGHT_ORDER.get((d / "type").read_text().strip(), 3)
            except OSError:
                return 3
        return min(dirs, key=rank) if dirs else None

    def _read_backlight(self) -> int | None:
        if self._backlight is None:
            return None
        try:
            return backlight_percent((self._backlight / "brightness").read_text(),
                                     (self._backlight / "max_brightness").read_text())
        except OSError:
            return None

    def _brightness_moved(self) -> None:
        value = self._read_backlight()
        if value is not None and value != self._brightness:
            self.changed.emit("parlaklik", value, False)
        if value is not None:
            self._brightness = value

    def _read_monitor(self) -> None:
        for line in self._lines("gdbus", self._monitor):
            if is_screen_changed(line):
                QTimer.singleShot(60, self._brightness_moved)      # let the new value land
                continue
            value = parse_brightness(line)
            if value is not None and value != self._brightness:
                self._brightness = value
                self.changed.emit("parlaklik", value, False)
