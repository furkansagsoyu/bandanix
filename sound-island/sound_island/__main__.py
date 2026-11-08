"""Entry point: `python -m sound_island [--player NAME]`."""

from __future__ import annotations

import argparse
import shutil
import signal
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="sound-island",
        description="Linux'ta MPRIS oynatıcıları için yüzen \"şimdi çalıyor\" adası (Bandanix'in parçası).")
    parser.add_argument("--player", default="spotify",
                        help="`playerctl -l` çıktısındaki oynatıcı adı (varsayılan: spotify)")
    args = parser.parse_args()

    if shutil.which("playerctl") is None:
        print("playerctl bulunamadı. Kurmak için: sudo apt install playerctl",
              file=sys.stderr)
        return 1

    from PySide6.QtCore import QDir, QLockFile
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication

    from .config import load_theme
    from .player import Player
    from .ui import Island

    lock = QLockFile(QDir.tempPath() + f"/bandanix-sound-island-{args.player}.lock")
    if not lock.tryLock(100):
        print("Sound Island zaten çalışıyor.", file=sys.stderr)
        return 0

    signal.signal(signal.SIGINT, signal.SIG_DFL)  # Ctrl+C in the terminal quits
    app = QApplication(sys.argv)
    app.setApplicationName("Sound Island")
    app.setDesktopFileName("bandanix-sound-island")

    theme = load_theme()
    if theme.font:
        app.setFont(QFont(theme.font))

    player = Player(args.player)
    island = Island(player, theme)
    if not theme.hide_when_idle:
        island.show()
    player.start()
    app.aboutToQuit.connect(player.stop)
    if theme.gosterge:
        from .gosterge import Levels
        levels = Levels(app)
        levels.changed.connect(island.show_level)
        levels.start()
        app.aboutToQuit.connect(levels.stop)
    app.aboutToQuit.connect(island.shutdown)
    code = app.exec()
    lock.unlock()
    return code


if __name__ == "__main__":
    sys.exit(main())
