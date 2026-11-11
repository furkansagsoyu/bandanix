"""Entry point: `python -m sound_island [--player NAME]`."""

from __future__ import annotations

import argparse
import shutil
import signal
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="sound-island",
        description="Bandanix ekran adası.")
    parser.add_argument("--player", default="spotify",
                        help="`playerctl -l` çıktısındaki oynatıcı adı (varsayılan: spotify)")
    args = parser.parse_args()

    if shutil.which("playerctl") is None:
        print("playerctl bulunamadı. Kurmak için: sudo apt install playerctl",
              file=sys.stderr)
        return 1

    from PySide6.QtCore import QLockFile, QTimer
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication

    from bandanix_ada import dizilim

    sys.path.append(str(Path(__file__).resolve().parents[2] / "core"))
    from .config import load_theme
    from .player import Player
    from .shortcuts import ShortcutServer
    from .ui import Island

    runtime = dizilim.folder()
    runtime.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(runtime / "sound-island.lock"))
    if not lock.tryLock(100):
        print("Sound Island zaten çalışıyor.", file=sys.stderr)
        return 0

    app = QApplication(sys.argv)
    app.setApplicationName("Bandanix Adası")
    app.setDesktopFileName("bandanix-sound-island")
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    signal.signal(signal.SIGTERM, lambda *_: app.quit())
    # Qt beklerken de Python sinyal işleyicisine dön.
    signals = QTimer(app)
    signals.timeout.connect(lambda: None)
    signals.start(200)

    theme = load_theme()
    if theme.font:
        app.setFont(QFont(theme.font))

    player = Player(args.player)
    island = Island(player, theme)
    island.show()
    shortcuts = ShortcutServer(island)
    if shortcuts.start():
        app.aboutToQuit.connect(shortcuts.close)
    else:
        print("Sound Island: pano ve not kısayolları bağlanamadı.", file=sys.stderr)
    island.notifications.start()
    player.start()
    app.aboutToQuit.connect(player.stop)
    island.level_monitor.start(monitor_brightness=theme.gosterge)
    app.aboutToQuit.connect(island.shutdown)
    code = app.exec()
    lock.unlock()
    return code


if __name__ == "__main__":
    sys.exit(main())
