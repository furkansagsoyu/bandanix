"""Installer, settings file, background copy and the Brave check, in a throwaway home folder."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent


class SekmeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        bin_dir = self.home / "stubs"
        bin_dir.mkdir()
        for utility in ("bash", "basename", "cat", "chmod", "cp", "dirname", "mkdir", "rm", "wc"):
            (bin_dir / utility).symlink_to(Path("/usr/bin") / utility)
        self.wall = self.home / "Resimler" / "deneme duvar.jpg"
        self.wall.parent.mkdir()
        self.wall.write_bytes((REPO / "duvar-kagidi/resimler/galata.jpg").read_bytes())
        (bin_dir / "dconf").write_text(f"#!/bin/sh\necho \"'file://{self.wall.parent}/deneme%20duvar.jpg'\"\n")
        (bin_dir / "dconf").chmod(0o755)
        (self.home / ".config/bandanix").mkdir(parents=True)
        (self.home / ".config/bandanix/theme.toml").write_text('[colors]\naccent = "#1E90FF"\n[fonts]\nui = "Inter"\n')
        self.env = {"HOME": str(self.home), "PATH": str(bin_dir), "LANG": "C.UTF-8"}
        self.ext = self.home / ".local/share/bandanix/yeni-sekme/eklenti"

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, *cmd):
        return subprocess.run(list(cmd), env=self.env, capture_output=True, text=True)

    def settings(self):
        text = (self.ext / "ayar.js").read_text(encoding="utf-8")
        return json.loads(text[text.index("{"):text.rindex("}") + 1])

    def test_install_update_and_brave_check(self):
        r = self.run_cmd(str(HERE / "install.sh"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Paketlenmemiş öğe yükle", r.stdout)
        self.assertIn("Brave bulunamadı", r.stdout)
        self.assertTrue((self.ext / "manifest.json").is_file())
        self.assertTrue((self.ext / "arka-plan.jpg").is_file())
        s = self.settings()
        self.assertEqual((s["accent"], s["font"], s["kaynak"]), ("#1E90FF", "Inter", "deneme duvar"))
        self.assertTrue(s["arkaPlan"].startswith("arka-plan.jpg?v="))

        theme = self.home / ".local/share/bandanix/yeni-sekme/tema"
        self.assertTrue((theme / "manifest.json").is_file())
        self.assertIn(str(self.ext), r.stdout)
        self.assertIn(str(theme), r.stdout)
        self.assertIn("İkinci klasör", r.stdout)

        sekme = str(self.home / ".local/bin/bandanix-sekme")
        self.assertIn("Brave hiç açılmamış", self.run_cmd(sekme).stdout)
        prefs = self.home / ".config/BraveSoftware/Brave-Browser/Default/Secure Preferences"
        prefs.parent.mkdir(parents=True)

        # the page is loaded (as on Furkan's Brave), the theme not yet: only the theme's step is shown
        prefs.write_text(json.dumps({"extensions": {"settings": {"abc": {"path": str(self.ext)}}}}))
        lines = self.run_cmd(sekme).stdout.splitlines()
        self.assertEqual(lines[0].split(None, 2)[2], "Brave'de yüklü")
        self.assertIn("yüklü değil", lines[1])
        r = self.run_cmd(str(HERE / "install.sh"))
        self.assertIn(str(theme), r.stdout)
        self.assertNotIn(f"Yeni sekme  {self.ext}", r.stdout)
        self.assertNotIn("İkinci klasör", r.stdout)
        self.assertNotIn("Değişiklikleri koru", r.stdout)

        # both loaded: no instructions at all
        prefs.write_text(json.dumps({"extensions": {"settings": {"abc": {"path": str(self.ext)},
                                                                  "def": {"path": str(theme)}}}}))
        r = self.run_cmd(str(HERE / "install.sh"))
        self.assertIn("zaten yüklü", r.stdout)

        # bandanix-duvar hands over a png
        png = self.home / "yeni.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n")
        self.assertEqual(self.run_cmd(sekme, "_arka-plan", str(png)).returncode, 0)
        self.assertFalse((self.ext / "arka-plan.jpg").exists())
        self.assertTrue((self.ext / "arka-plan.png").is_file())
        self.assertEqual(self.settings()["kaynak"], "yeni")

        r = self.run_cmd(str(HERE / "uninstall.sh"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.ext.exists())
        self.assertFalse((self.home / ".local/bin/bandanix-sekme").exists())

    def test_bad_theme_values_fall_back(self):
        (self.home / ".config/bandanix/theme.toml").write_text('[colors]\naccent = "red"\n[fonts]\nui = "x\\";alert(1)"\n')
        self.run_cmd(str(HERE / "install.sh"))
        s = self.settings()
        self.assertEqual((s["accent"], s["font"]), ("#C8102E", ""))

    def test_theme_manifest(self):
        m = json.loads((HERE / "tema/manifest.json").read_text(encoding="utf-8"))
        colors = m["theme"]["colors"]
        self.assertEqual(colors["toolbar"], [23, 23, 26])
        for key, value in colors.items():
            self.assertIn(len(value), (3, 4), key)
            self.assertTrue(all(isinstance(v, (int, float)) and 0 <= v <= 255 for v in value), key)
        self.assertNotIn("chrome_url_overrides", m)          # a theme may not carry anything else

    def test_manifest(self):
        m = json.loads((HERE / "eklenti/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(m["manifest_version"], 3)
        self.assertEqual(m["chrome_url_overrides"]["newtab"], "sekme.html")
        for name in ("sekme.html", "sekme.css", "sekme.js", "ayar.js", m["icons"]["128"]):
            self.assertTrue((HERE / "eklenti" / name).is_file(), name)
        html = (HERE / "eklenti/sekme.html").read_text(encoding="utf-8")
        self.assertNotRegex(html, r"<script>(?!</script>)")      # MV3 forbids inline scripts


if __name__ == "__main__":
    unittest.main()
