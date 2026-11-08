"""Tests for the login screen settings editor: python3 -m unittest discover giris-ekrani/tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bandanix_giris as g  # noqa: E402


class Conf(unittest.TestCase):
    def test_keeps_other_lines(self):
        old = "[Greeter]\n# yorum\nbackground=/eski.jpg\nshow-hostname=true\n\n[Diger]\nx=1\n"
        new = g.set_keys(old, {"background": "/yeni.png", "draw-grid": "false"})
        self.assertIn("# yorum", new)
        self.assertIn("show-hostname=true", new)
        self.assertIn("[Diger]\nx=1", new)
        self.assertEqual(g.read_keys(new), {"background": "/yeni.png", "show-hostname": "true",
                                            "draw-grid": "false"})

    def test_empty_file_and_removal(self):
        new = g.set_keys("", {"background": "/a.png"})
        self.assertEqual(new, "[Greeter]\nbackground=/a.png\n")
        self.assertEqual(g.read_keys(g.set_keys(new, {"background": None})), {})

    def test_wallpaper_name(self):
        self.assertTrue(g.WALL_RE.match("bandanix-logo-ogle.png"))
        self.assertFalse(g.WALL_RE.match("benim-resmim.png"))


if __name__ == "__main__":
    unittest.main()
