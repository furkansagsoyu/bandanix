"""Tests for the settings app's non-GUI parts: python3 -m unittest discover ayarlar/tests"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

TMP = Path(tempfile.mkdtemp())
os.environ["HOME"] = str(TMP)
os.environ["XDG_CONFIG_HOME"] = str(TMP / "config")
os.environ["XDG_DATA_HOME"] = str(TMP / "data")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bandanix_ayarlar import ortam  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


class Theme(unittest.TestCase):
    def setUp(self):
        ortam.THEME.parent.mkdir(parents=True, exist_ok=True)

    def test_keeps_comments_even_with_quotes(self):
        ortam.THEME.write_text('[colors]\naccent = "#C8102E"        # bandana kırmızısı; "#RRGGBB" biçiminde\n\n'
                               '[panel]\nyukseklik = 54            # 40-64\n')
        ortam.set_values("colors", {"accent": "#3366FF"})
        ortam.set_values("panel", {"yukseklik": 58, "duzen": "uc-ada"})
        text = ortam.THEME.read_text()
        self.assertIn('accent = "#3366FF"        # bandana kırmızısı; "#RRGGBB" biçiminde', text)
        self.assertIn("yukseklik = 58            # 40-64", text)
        self.assertEqual(ortam.get("panel", "duzen", ""), "uc-ada")

    def test_new_section_and_types(self):
        ortam.THEME.write_text("[colors]\naccent = \"#C8102E\"\n")
        ortam.set_values("sound-island", {"gosterge": False, "bars": "simulated"})
        data = ortam.load()
        self.assertIs(data["sound-island"]["gosterge"], False)
        self.assertEqual(ortam.get("sound-island", "bars", "auto"), "simulated")
        self.assertEqual(ortam.get("panel", "yukseklik", 54), 54)          # missing -> default
        self.assertEqual(ortam.get("sound-island", "gosterge", 3), 3)      # wrong type -> default

    def test_section_in_middle(self):
        ortam.THEME.write_text("[a]\nx = 1\n\n[pil]\nust = 80\n\n[b]\ny = 2\n")
        ortam.set_values("pil", {"alt": 15})
        text = ortam.THEME.read_text()
        self.assertLess(text.index("alt = 15"), text.index("[b]"))
        self.assertEqual(ortam.load()["b"]["y"], 2)


class Components(unittest.TestCase):
    def test_repo_components_have_markers(self):
        comps = ortam.components(REPO)
        ids = [c["id"] for c in comps]
        self.assertIn("sound-island", ids)
        self.assertIn("ayarlar", ids)
        for c in comps:
            self.assertTrue(c["aciklama"], c["id"])
            text = (REPO / c["id"] / "install.sh").read_text()
            self.assertIn("# kurulu:", text, c["id"])

    def test_installed_marker(self):
        self.assertFalse(ortam.installed("pano"))
        (TMP / ".local" / "bin").mkdir(parents=True, exist_ok=True)
        (TMP / ".local" / "bin" / "bandanix-pano").touch()
        self.assertTrue(ortam.installed("pano"))

    def test_pretty_accel(self):
        self.assertEqual(ortam.pretty_accel("<Super>v"), "Super+V")
        self.assertEqual(ortam.pretty_accel("<Primary><Alt>n"), "Ctrl+Alt+N")
        self.assertEqual(ortam.pretty_accel(""), "—")


if __name__ == "__main__":
    unittest.main()
