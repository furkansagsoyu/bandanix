"""Kullanıcının başlattığı sessiz X11 ekran kaydı."""
from __future__ import annotations

import os
import signal
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QStandardPaths, Signal

from .desktop import command


class ScreenCapture(QObject):
    changed = Signal()

    def __init__(self, parent: QObject):
        super().__init__(parent)
        self.program = command("gst-launch-1.0")
        self.screenshot = command("gnome-screenshot")
        self.path: Path | None = None
        self.status = ""
        self.stopping = False
        self.process = QProcess(self)
        self.process.setStandardOutputFile(QProcess.nullDevice())
        self.process.setStandardErrorFile(QProcess.nullDevice())
        self.process.started.connect(self.changed)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._failed)

    @property
    def recording(self) -> bool:
        return self.process.state() != QProcess.ProcessState.NotRunning

    def toggle(self) -> None:
        if self.recording:
            self.stop()
            return
        if not self.program:
            return
        videos = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.MoviesLocation)
        folder = Path(videos) if videos else Path.home() / "Videolar"
        try:
            folder.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=folder, prefix="bandanix-", suffix=".webm",
                                             delete=False) as file:
                self.path = Path(file.name)
        except OSError:
            self.status = "Kayıt dosyası açılamadı"
            self.changed.emit()
            return
        self.stopping = False
        self.status = "Kayıt sürüyor · sessiz WebM"
        self.process.start(self.program, [
            "-q", "-e", "ximagesrc", "use-damage=true", "!", "videoconvert", "!",
            "video/x-raw,framerate=30/1", "!", "vp8enc", "deadline=1", "!",
            "webmmux", "!", "filesink", f"location={self.path}",
        ])
        self.changed.emit()

    def stop(self) -> None:
        if not self.recording or self.stopping:
            return
        pid = self.process.processId()
        if not pid:
            return
        self.stopping = True
        self.status = "Kayıt kaydediliyor…"
        try:
            os.kill(pid, signal.SIGINT)  # gst-launch -e, dosyayı kapatmadan önce EOS gönderir.
        except ProcessLookupError:
            pass
        self.changed.emit()

    def shutdown(self) -> None:
        if self.recording:
            self.stop()
            if not self.process.waitForFinished(2500):
                self.process.kill()
                self.process.waitForFinished(500)

    def _failed(self, error) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self._finished(1, QProcess.ExitStatus.CrashExit)

    def _finished(self, code, exit_status) -> None:
        try:
            saved = self.path is not None and self.path.stat().st_size > 0
            if self.path is not None and not saved:
                self.path.unlink(missing_ok=True)
        except OSError:
            saved = False
        if saved and self.stopping and exit_status == QProcess.ExitStatus.NormalExit:
            self.status = f"Videolar · {self.path.name}"
        else:
            self.status = "Ekran kaydı tamamlanamadı"
        self.path = None
        self.stopping = False
        self.changed.emit()
