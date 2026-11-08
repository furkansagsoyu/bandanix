"""Tests for the clipboard history store: python3 -m unittest discover pano/tests"""
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["XDG_DATA_HOME"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pano_gecmis as pano  # noqa: E402


class Store(unittest.TestCase):
    def setUp(self):
        pano.FILE.unlink(missing_ok=True)

    def texts(self):
        return [i["metin"] for i in pano.items()]

    def test_newest_first_and_dedupe(self):
        pano.add("a", 1)
        pano.add("b", 2)
        pano.add("a", 3)
        self.assertEqual(self.texts(), ["a", "b"])

    def test_private_file(self):
        pano.add("gizli", 1)
        self.assertEqual(stat.S_IMODE(os.stat(pano.FILE).st_mode), 0o600)

    def test_skips(self):
        self.assertFalse(pano.acceptable("  \n"))
        self.assertFalse(pano.acceptable("x" * (pano.MAX_CHARS + 1)))
        self.assertFalse(pano.acceptable("sifre", ["UTF8_STRING", pano.PASSWORD_HINT]))
        self.assertTrue(pano.acceptable("normal", ["UTF8_STRING"]))

    def test_limit_keeps_pinned(self):
        pano.add("IBAN", 0)
        pano.toggle_pin("IBAN")
        for n in range(pano.LIMIT + 10):
            pano.add(f"k{n}", 1 + n)
        data = pano.items()
        self.assertEqual(len(data), pano.LIMIT + 1)
        self.assertEqual((data[0]["metin"], data[0]["sabit"]), ("IBAN", True))
        self.assertEqual(pano.clear(), pano.LIMIT)
        self.assertEqual(self.texts(), ["IBAN"])

    def test_delete(self):
        pano.add("a", 1)
        self.assertTrue(pano.delete("a"))
        self.assertFalse(pano.delete("a"))


class Display(unittest.TestCase):
    def test_turkish_search(self):
        self.assertTrue(pano.matches("İstanbul adresi", "istanbul"))
        self.assertTrue(pano.matches("ISPARTA", "ısparta"))
        self.assertTrue(pano.matches("kod: 1234 ankara", "ankara 12"))
        self.assertFalse(pano.matches("ankara", "izmir"))

    def test_title(self):
        self.assertEqual(pano.title("  ilk   satır \n ikinci"), "ilk satır …")

    def test_paste_keys(self):
        self.assertEqual(pano.paste_keys("gnome-terminal-server"), "ctrl+shift+v")
        self.assertEqual(pano.paste_keys("Brave-browser"), "ctrl+v")


if __name__ == "__main__":
    unittest.main()
