"""Bildirim köprüsünü ayrı D-Bus oturumunda ve geçici ayarlarla dener."""
from __future__ import annotations

import json
import os
import selectors
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BRIDGE = Path(__file__).resolve().parents[1] / "sound_island" / "notification_bridge.py"
SETTINGS = ["gsettings", "get", "org.cinnamon.desktop.notifications", "display-notifications"]
PYTHON = "/usr/bin/python3"


class BridgeTests(unittest.TestCase):
    def test_cinnamon_popups_are_restored(self):
        if not Path(PYTHON).is_file() or not all(shutil.which(tool) for tool in
                                                ("dbus-run-session", "gdbus", "gsettings")):
            self.skipTest("Cinnamon oturum araçları yok")
        with tempfile.TemporaryDirectory() as folder:
            env = {**os.environ, "XDG_RUNTIME_DIR": folder, "XDG_CONFIG_HOME": folder,
                   "GIO_USE_VFS": "local", "GSETTINGS_BACKEND": "keyfile"}
            if subprocess.run(SETTINGS, env=env, capture_output=True).returncode:
                self.skipTest("Cinnamon bildirim şeması yok")
            result = subprocess.run(
                ["dbus-run-session", "--", PYTHON, str(Path(__file__).resolve()), "--bridge"],
                env=env, capture_output=True, text=True, timeout=15,
            )
        self.assertEqual(result.returncode, 0, result.stderr)


def check_bridge():
    def enabled():
        return subprocess.check_output(SETTINGS).strip() == b"true"

    assert enabled()
    proc = subprocess.Popen([PYTHON, str(BRIDGE)], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        with selectors.DefaultSelector() as sel:
            sel.register(proc.stdout, selectors.EVENT_READ)

            def receive():
                assert sel.select(4), "Köprüden veri gelmedi"
                return json.loads(proc.stdout.readline())

            assert receive() == {"ready": True}
            assert not enabled()
            subprocess.run(
                ["gdbus", "call", "--session", "--dest", "org.freedesktop.Notifications",
                 "--object-path", "/org/freedesktop/Notifications", "--method",
                 "org.freedesktop.Notifications.Notify", "Test", "uint32 0", "",
                 "Başlık", "Gövde", "@as []", "@a{sv} {}", "1000"],
                capture_output=True, timeout=3,
            )
            assert receive() == {"app": "Test", "summary": "Başlık", "body": "Gövde"}
        proc.stdin.close()
        assert proc.wait(timeout=4) == 0
        assert enabled()
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=4)
        proc.stdin.close()
        proc.stdout.close()


if __name__ == "__main__":
    if sys.argv[1:] == ["--bridge"]:
        check_bridge()
    else:
        unittest.main()
