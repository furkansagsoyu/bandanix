"""Synced lyrics from LRCLIB (https://lrclib.net), a free API with no key."""

from __future__ import annotations

import json
from urllib.parse import urlencode

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest

from .parsing import Track, parse_lrc, pick_search_result

API = "https://lrclib.net/api"
USER_AGENT = b"sound-island/0.1 (https://github.com/furkansagsoyu/sound-island)"


class LyricsFetcher(QObject):
    ready = Signal(str, list)  # track_id, [(seconds, line), ...] (empty = none found)

    def __init__(self, nam: QNetworkAccessManager, parent: QObject | None = None):
        super().__init__(parent)
        self.nam = nam
        self.cache: dict[str, list] = {}

    def fetch(self, track: Track) -> None:
        if track.track_id in self.cache:
            self.ready.emit(track.track_id, self.cache[track.track_id])
            return
        params = {"track_name": track.title, "artist_name": track.artist}
        if track.album:
            params["album_name"] = track.album
        if track.length > 0:
            params["duration"] = str(round(track.length))
        self._get("/get", params, lambda status, data: self._on_get(track, status, data))

    def _get(self, path: str, params: dict, callback) -> None:
        request = QNetworkRequest(QUrl(f"{API}{path}?{urlencode(params)}"))
        request.setRawHeader(b"User-Agent", USER_AGENT)
        reply = self.nam.get(request)

        def done():
            status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute) or 0
            data = bytes(reply.readAll())
            reply.deleteLater()
            callback(int(status), data)

        reply.finished.connect(done)

    def _on_get(self, track: Track, status: int, data: bytes) -> None:
        if status == 200:
            try:
                obj = json.loads(data)
            except ValueError:
                obj = None
            if isinstance(obj, dict):
                lines = parse_lrc(obj.get("syncedLyrics") or "")
                if lines:
                    self._done(track, lines)
                    return
        # exact match failed: try a looser search
        params = {"track_name": track.title, "artist_name": track.artist}
        self._get("/search", params, lambda s, d: self._on_search(track, s, d))

    def _on_search(self, track: Track, status: int, data: bytes) -> None:
        lines: list = []
        if status == 200:
            try:
                items = json.loads(data)
            except ValueError:
                items = []
            best = pick_search_result(items, track.length)
            if best:
                lines = parse_lrc(best.get("syncedLyrics") or "")
        self._done(track, lines)

    def _done(self, track: Track, lines: list) -> None:
        self.cache[track.track_id] = lines
        self.ready.emit(track.track_id, lines)
