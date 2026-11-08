"""Talks to any MPRIS media player through the `playerctl` command."""

from __future__ import annotations

from PySide6.QtCore import QElapsedTimer, QObject, QProcess, QTimer, Signal

from .parsing import (FOLLOW_FORMAT, POLL_FORMAT, Track, parse_metadata_line,
                      parse_poll_line)


class Player(QObject):
    trackChanged = Signal(object)   # new song (Track) or None when nothing plays
    trackUpdated = Signal(object)   # same song, details changed (e.g. cover arrived late)
    statusChanged = Signal(str)     # "Playing" / "Paused" / "Stopped" / ""

    def __init__(self, name: str = "spotify", parent: QObject | None = None):
        super().__init__(parent)
        self.name = name
        self.track: Track | None = None
        self.status = ""
        self._pos = 0.0
        self._clock = QElapsedTimer()
        self._clock.start()
        self._buf = b""
        self._stopping = False

        # Long-running `--follow` process: pushes a line on every change.
        self._follow = QProcess(self)
        self._follow.readyReadStandardOutput.connect(self._read_follow)
        self._follow.finished.connect(self._follow_finished)

        # Short poll for position (and status, as a safety net).
        self._pollproc = QProcess(self)
        self._pollproc.finished.connect(self._read_poll)
        self._poll = QTimer(self)
        self._poll.setInterval(1000)
        self._poll.timeout.connect(self._poll_now)

    # ---- lifecycle -------------------------------------------------------
    def start(self) -> None:
        self._start_follow()
        self._poll.start()

    def stop(self) -> None:
        self._stopping = True
        self._poll.stop()
        for proc in (self._follow, self._pollproc):
            if proc.state() != QProcess.ProcessState.NotRunning:
                proc.kill()
                proc.waitForFinished(500)

    def _start_follow(self) -> None:
        if self._stopping or self._follow.state() != QProcess.ProcessState.NotRunning:
            return
        self._buf = b""
        self._follow.start("playerctl", ["-p", self.name, "metadata",
                                         "--follow", "--format", FOLLOW_FORMAT])

    def _follow_finished(self, *_):
        if not self._stopping:
            QTimer.singleShot(2000, self._start_follow)

    # ---- reading ---------------------------------------------------------
    def _read_follow(self) -> None:
        self._buf += bytes(self._follow.readAllStandardOutput())
        while b"\n" in self._buf:
            raw, self._buf = self._buf.split(b"\n", 1)
            status, track = parse_metadata_line(raw.decode("utf-8", "replace"))
            self._apply(status, track)

    def _apply(self, status: str, track: Track | None) -> None:
        old = self.track
        if track is None:
            if old is not None:
                self.track = None
                self.trackChanged.emit(None)
        elif old is None or track.track_id != old.track_id:
            self.track = track
            self._set_pos(0.0)
            self.trackChanged.emit(track)
            self._poll_now()
        elif track != old:
            self.track = track
            self.trackUpdated.emit(track)
        self._set_status(status if track is not None else "")

    def _set_status(self, status: str) -> None:
        if status != self.status:
            self.status = status
            self.statusChanged.emit(status)
            self._poll_now()

    def _poll_now(self) -> None:
        if self.track is None or self._pollproc.state() != QProcess.ProcessState.NotRunning:
            return
        self._pollproc.start("playerctl", ["-p", self.name, "metadata",
                                           "--format", POLL_FORMAT])

    def _read_poll(self, *_):
        out = bytes(self._pollproc.readAllStandardOutput()).decode("utf-8", "replace")
        status, pos = parse_poll_line(out)
        if pos is not None:
            self._set_pos(pos)
        if status and self.track is not None:
            self._set_status(status)

    def _set_pos(self, seconds: float) -> None:
        self._pos = seconds
        self._clock.restart()

    # ---- queries & controls ---------------------------------------------
    def position(self) -> float:
        pos = self._pos
        if self.status == "Playing":
            pos += self._clock.elapsed() / 1000
        length = self.track.length if self.track else 0.0
        return min(pos, length) if length > 0 else pos

    def _cmd(self, *args: str) -> None:
        QProcess.startDetached("playerctl", ["-p", self.name, *args])

    def play_pause(self) -> None:
        self._cmd("play-pause")

    def next(self) -> None:
        self._cmd("next")

    def previous(self) -> None:
        self._cmd("previous")

    def seek(self, seconds: float) -> None:
        seconds = max(0, int(seconds))  # whole seconds: avoids locale decimal issues
        self._cmd("position", str(seconds))
        self._set_pos(float(seconds))
