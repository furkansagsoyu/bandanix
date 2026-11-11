"""Bildirim köprüsünün Qt tarafı. Geçmiş yalnızca bellekte tutulur."""
from __future__ import annotations

import html
import json
import re
from collections import deque
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal


MARKUP = re.compile(r"</?(?:b|i|u|a)(?:\s+[^>]*)?>|<img\s+[^>]*>", re.IGNORECASE)


class Notifications(QObject):
    changed = Signal()

    def __init__(self, parent: QObject):
        super().__init__(parent)
        self.items: deque[dict] = deque(maxlen=50)
        self.ready = False
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.ForwardedErrorChannel)
        self.process.readyReadStandardOutput.connect(self._read)
        self.process.finished.connect(self._offline)
        self.process.errorOccurred.connect(self._offline)

    def add(self, app: str, summary: str, body: str) -> None:
        self.items.appendleft({"app": app, "summary": summary, "body": body})
        self.changed.emit()

    def start(self) -> None:
        self.process.start("/usr/bin/python3", [str(Path(__file__).with_name("notification_bridge.py"))])

    def stop(self) -> None:
        if self.process.state() == QProcess.ProcessState.NotRunning:
            return
        self.process.closeWriteChannel()
        if not self.process.waitForFinished(1000):
            self.process.terminate()
            self.process.waitForFinished(1000)

    def _offline(self, *_) -> None:
        self.ready = False
        self.changed.emit()

    def _read(self) -> None:
        while self.process.canReadLine():
            try:
                item = json.loads(bytes(self.process.readLine()))
            except ValueError:
                continue
            if not isinstance(item, dict):
                continue
            if item.get("ready"):
                self.ready = True
            elif all(isinstance(item.get(key), str) for key in ("app", "summary", "body")):
                self.add(item["app"], item["summary"], html.unescape(MARKUP.sub("", item["body"])))
                continue
            else:
                continue
            self.changed.emit()
