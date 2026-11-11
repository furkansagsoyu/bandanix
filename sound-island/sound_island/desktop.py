"""Adanın hava durumu önbelleği ve masaüstü kontrolleri."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

POWER = "org.cinnamon.SettingsDaemon.Power"
SCREEN = POWER + ".Screen"


def command(name: str) -> str | None:
    local = Path.home() / ".local/bin" / name
    return shutil.which(name) or (str(local) if os.access(local, os.X_OK) else None)


def weather() -> dict:
    cache = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    try:
        data = json.loads((cache / "bandanix/hava.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


class WeatherRefresh(QObject):
    """Saat widget'ı kurulu değilse aynı hava durumu yardımcısını çalıştırır."""

    def __init__(self, parent: QObject):
        super().__init__(parent)
        self.helper = Path(__file__).resolve().parents[1] / "bandanix_widget.py"
        self.process = QProcess(self)
        self.process.setStandardOutputFile(QProcess.nullDevice())
        self.process.setStandardErrorFile(QProcess.nullDevice())
        if self.helper.is_file() and not command("bandanix-widget"):
            self.timer = QTimer(self)
            self.timer.setInterval(30 * 60 * 1000)
            self.timer.timeout.connect(self.refresh)
            self.timer.start()
            updated = weather().get("son_deneme")
            if not isinstance(updated, (int, float)) or time.time() - updated >= 30 * 60:
                self.refresh()

    def refresh(self) -> None:
        if self.process.state() == QProcess.ProcessState.NotRunning:
            self.process.start("/usr/bin/python3", [str(self.helper), "_zamanlayici"])

    def stop(self) -> None:
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.terminate()
            self.process.waitForFinished(500)


class Brightness(QObject):
    changed = Signal()

    def __init__(self, parent: QObject):
        super().__init__(parent)
        self.value: int | None = None
        self.process = QProcess(self)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._failed)

    def request(self, step: int = 0) -> None:
        if self.process.state() != QProcess.ProcessState.NotRunning:
            return
        method = {0: "GetPercentage", -1: "StepDown", 1: "StepUp"}[step]
        self.process.start("gdbus", ["call", "--session", "--timeout", "2", "--dest", POWER,
                                     "--object-path", "/org/cinnamon/SettingsDaemon/Power",
                                     "--method", f"{SCREEN}.{method}"])

    def _failed(self, *_):
        self.value = None
        self.changed.emit()

    def _finished(self, code, _status):
        output = bytes(self.process.readAllStandardOutput()).decode("utf-8", "replace")
        self.process.readAllStandardError()
        parts = output.strip("(), \r\n").split()
        value = parts[-1] if parts else ""
        self.value = int(value) if code == 0 and value.isdecimal() else None
        self.changed.emit()


def active_window() -> str | None:
    output = x_property("-root", "_NET_ACTIVE_WINDOW")
    if match := re.search(r"\b0x[1-9a-f][0-9a-f]*\b", output, re.IGNORECASE):
        return match[0]
    return None


def window_classes(window: str) -> list[str]:
    return re.findall(r'"([^"]+)"', x_property("-id", window, "WM_CLASS"))


def x_property(*args: str) -> str:
    try:
        return subprocess.run(["xprop", *args], capture_output=True, text=True,
                              timeout=0.3, check=False).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""
