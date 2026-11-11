"""Kısayol komutlarını çalışan ada penceresine aktarır."""
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtNetwork import QLocalServer

from bandanix_ada_istek import PANELS, socket_path


class ShortcutServer(QLocalServer):
    def __init__(self, island):
        super().__init__(island)
        self.island = island
        self.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self.newConnection.connect(self._accept)

    def start(self) -> bool:
        try:
            path = str(socket_path())
        except OSError:
            return False
        self.removeServer(path)  # tek ada kilidi alınmışken eski soketi temizle
        return self.listen(path)

    def _accept(self) -> None:
        while self.hasPendingConnections():
            client = self.nextPendingConnection()
            client.setReadBufferSize(32)
            client.disconnected.connect(client.deleteLater)
            client.readyRead.connect(lambda sock=client: self._read(sock))
            timeout = QTimer(client)
            timeout.setSingleShot(True)
            timeout.timeout.connect(lambda sock=client: sock.abort())
            timeout.start(1000)
            self._read(client)

    def _read(self, client) -> None:
        if not client.canReadLine():
            return
        command = bytes(client.readLine()).strip()
        accepted = False
        for panel in PANELS:
            if command == panel.encode("ascii"):
                accepted = self.island.open_tool(panel, toggle=True)
                break
        client.write(b"ok\n" if accepted else b"no\n")
        client.disconnectFromServer()
