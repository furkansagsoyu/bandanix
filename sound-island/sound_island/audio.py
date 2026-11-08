"""Real audio levels from cava (https://github.com/karlstav/cava).

cava listens to what your speakers play (PulseAudio / PipeWire) and prints
bar heights. We only run it while music is playing, so it costs nothing at rest.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from PySide6.QtCore import QElapsedTimer, QObject, QProcess

from .parsing import parse_cava_frame

CONFIG = """\
[general]
bars = {bars}
framerate = 30
autosens = 1
lower_cutoff_freq = 50
higher_cutoff_freq = 10000

[input]
method = pulse
source = auto

[output]
channels = mono
mono_option = average
method = raw
raw_target = /dev/stdout
data_format = ascii
ascii_max_range = 100
bar_delimiter = 59
frame_delimiter = 10

[smoothing]
noise_reduction = 70
"""


class AudioBars(QObject):
    def __init__(self, count: int, parent: QObject | None = None):
        super().__init__(parent)
        self.count = count
        self.levels: list[float] = [0.0] * count
        self.failed = False
        self._buf = b""
        self._fresh = QElapsedTimer()
        self._config = Path(tempfile.gettempdir()) / "bandanix-sound-island-cava.conf"
        self._proc = QProcess(self)
        self._proc.setStandardErrorFile(QProcess.nullDevice())   # don't buffer cava's warnings
        self._proc.readyReadStandardOutput.connect(self._read)
        self._proc.finished.connect(self._finished)
        self._stopping = False

    @staticmethod
    def available() -> bool:
        return shutil.which("cava") is not None

    def live(self) -> bool:
        """True while cava is delivering frames (last one under 300 ms ago)."""
        return self._fresh.isValid() and self._fresh.elapsed() < 300

    def start(self) -> None:
        if self.failed or self._proc.state() != QProcess.ProcessState.NotRunning:
            return
        self._config.write_text(CONFIG.format(bars=self.count), encoding="utf-8")
        self._stopping = False
        self._buf = b""
        self._proc.start("cava", ["-p", str(self._config)])

    def stop(self) -> None:
        self._stopping = True
        self._fresh.invalidate()
        if self._proc.state() != QProcess.ProcessState.NotRunning:
            self._proc.kill()
            self._proc.waitForFinished(500)

    def _read(self) -> None:
        self._buf += bytes(self._proc.readAllStandardOutput())
        if b"\n" not in self._buf:
            return
        *frames, self._buf = self._buf.split(b"\n")
        for raw in reversed(frames):           # newest complete frame wins
            levels = parse_cava_frame(raw.decode("ascii", "ignore"), self.count)
            if levels is not None:
                self.levels = levels
                self._fresh.restart()
                break

    def _finished(self, *_):
        if not self._stopping:
            # cava stopped on its own (no audio server, bad config...): fall back for good.
            self.failed = True
        self._fresh.invalidate()
