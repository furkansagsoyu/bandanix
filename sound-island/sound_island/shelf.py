"""Dosya rafında yalnızca kullanıcı tarafından eklenen yerel yollar tutulur."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, QUrl


class FileShelf:
    LIMIT = 18

    def __init__(self) -> None:
        self.settings = QSettings("Bandanix", "Ada")
        stored = self.settings.value("dosya-rafi", [], type=list)
        self.paths = [Path(path) for path in stored
                      if isinstance(path, str) and Path(path).is_absolute()][:self.LIMIT]

    @staticmethod
    def paths_from_urls(urls: list[QUrl]) -> list[Path]:
        paths = []
        for url in urls:
            if url.isLocalFile() and not url.host():
                path = Path(url.toLocalFile())
                if path.is_absolute() and path.is_file():
                    paths.append(path)
        return paths

    def add(self, paths: list[Path]) -> None:
        self.paths = list(dict.fromkeys([*paths, *self.paths]))[:self.LIMIT]
        self._save()

    def remove(self, index: int) -> None:
        self.paths.pop(index)
        self._save()

    def _save(self) -> None:
        self.settings.setValue("dosya-rafi", [str(path) for path in self.paths])
        self.settings.sync()
