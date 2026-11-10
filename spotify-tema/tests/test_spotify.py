"""bandanix-spotify with a fake Spotify folder and a stand-in spicetify that records its calls."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

SPICETIFY = r'''#!/bin/sh
echo "$*" >> "$LOG"
case "$*" in
  "-v") echo 2.40.0 ;;
  *"backup apply"*) if [ -f "$FAIL" ]; then echo "error Spotify version mismatch"; exit 1; fi; echo "success" ;;
esac
exit 0
'''


class SpotifyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.home, self.root, stubs = t / "home", t / "kok", t / "stubs"
        (self.root / "usr/share/spotify/Apps").mkdir(parents=True)
        (self.root / "usr/share/spotify/Apps/xpui.spa").write_bytes(b"x")
        (self.home / ".config/spotify").mkdir(parents=True)
        (self.home / ".config/spotify/prefs").write_text("x")
        (self.home / ".spicetify").mkdir()
        stubs.mkdir()
        self.log, self.fail, self.version = t / "log", t / "fail", t / "version"
        self.version.write_text("1:1.2.50")
        files = {
            self.home / ".spicetify/spicetify": SPICETIFY,
            stubs / "dpkg-query": f'#!/bin/sh\ncat "{self.version}"\n',
            stubs / "notify-send": f'#!/bin/sh\necho "notify $*" >> "{t}/notes"\n',
            stubs / "pgrep": "#!/bin/sh\nexit 1\n",
        }
        for path, body in files.items():
            path.write_text(body)
            path.chmod(0o755)
        self.notes = t / "notes"
        self.env = {"HOME": str(self.home), "BANDANIX_KOK": str(self.root), "LOG": str(self.log),
                    "FAIL": str(self.fail), "PATH": f"{stubs}:/usr/bin:/bin", "LANG": "C.UTF-8"}
        self.app = self.home / ".local/share/bandanix/spotify-tema"
        self.app.mkdir(parents=True)
        (self.app / "Bandanix").mkdir()
        for f in (HERE / "tema/Bandanix").iterdir():
            (self.app / "Bandanix" / f.name).write_bytes(f.read_bytes())

    def tearDown(self):
        self.tmp.cleanup()

    def cmd(self, *args):
        return subprocess.run(["/usr/bin/python3", str(HERE / "bandanix_spotify.py"), *args],
                              env=self.env, capture_output=True, text=True)

    def calls(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_apply_then_login_checks(self):
        r = self.cmd("uygula")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        calls = self.calls()
        config = next(c for c in calls if "current_theme" in c)
        self.assertIn("current_theme Bandanix color_scheme Bandanix", config)
        self.assertIn(f"spotify_path {self.root}/usr/share/spotify", config)
        self.assertIn("replace_colors 1", config)
        self.assertEqual(calls[-1], "-q backup apply")
        self.assertTrue((self.home / ".config/spicetify/Themes/Bandanix/color.ini").is_file())
        self.assertEqual(json.loads((self.app / "durum.json").read_text())["surum"], "1:1.2.50")
        self.assertIn("Tema         Bandanix", self.cmd().stdout)

        # login, same Spotify: nothing runs
        self.log.write_text("")
        self.assertEqual(self.cmd("_oturum").returncode, 0)
        self.assertEqual(self.calls(), [])

        # Spotify was updated: applied again without restarting Spotify
        self.version.write_text("1:1.2.51")
        self.assertIn("güncellenmiş", self.cmd().stdout)
        self.assertEqual(self.cmd("_oturum").returncode, 0)
        self.assertIn("-q --no-restart backup apply", self.calls())
        self.assertEqual(json.loads((self.app / "durum.json").read_text())["surum"], "1:1.2.51")

        # same Spotify again via uygula: a plain apply comes first
        self.log.write_text("")
        self.cmd("uygula")
        self.assertIn("-q apply", self.calls())

    def test_update_failure_tries_cli_upgrade_and_restore(self):
        self.fail.write_text("")
        r = self.cmd("uygula")
        self.assertEqual(r.returncode, 1)
        calls = self.calls()
        self.assertIn("-q upgrade", calls)
        self.assertIn("-q restore backup apply", calls)
        self.assertIn("uygulanamadı", r.stdout)
        self.assertFalse((self.app / "durum.json").exists())

    def test_login_failure_notifies(self):
        self.cmd("uygula")
        self.fail.write_text("")
        self.version.write_text("2")
        self.cmd("_oturum")
        self.assertIn("yeniden uygulanamadı", self.notes.read_text())

    def test_spotify_never_opened(self):
        (self.home / ".config/spotify/prefs").unlink()
        r = self.cmd("uygula")
        self.assertEqual(r.returncode, 1)
        self.assertIn("hiç açılmamış", r.stdout)

    def test_snap_and_missing(self):
        (self.root / "snap/bin").mkdir(parents=True)
        (self.root / "snap/bin/spotify").write_text("")
        self.assertEqual(self.cmd("_tur").stdout.strip(), "snap")
        self.assertIn("Snap", self.cmd("uygula").stdout)
        (self.root / "snap/bin/spotify").unlink()
        (self.root / "usr/share/spotify/Apps/xpui.spa").unlink()
        (self.root / "usr/share/spotify/Apps").rmdir()
        self.assertEqual(self.cmd("_tur").stdout.strip(), "yok")

    def test_flatpak_paths(self):
        (self.root / "usr/share/spotify/Apps/xpui.spa").unlink()
        (self.root / "usr/share/spotify/Apps").rmdir()
        flat = self.root / "var/lib/flatpak/app/com.spotify.Client/x86_64/stable/active/files/extra/share/spotify/Apps"
        flat.mkdir(parents=True)
        prefs = self.home / ".var/app/com.spotify.Client/config/spotify/prefs"
        prefs.parent.mkdir(parents=True)
        prefs.write_text("x")
        self.cmd("uygula")
        config = next(c for c in self.calls() if "current_theme" in c)
        self.assertIn(f"spotify_path {flat.parent}", config)
        self.assertIn(f"prefs_path {prefs}", config)

    def test_restore(self):
        self.cmd("uygula")
        self.assertEqual(self.cmd("geri").returncode, 0)
        self.assertEqual(self.calls()[-1], "-q restore")
        self.assertFalse((self.app / "durum.json").exists())

    def test_colour_scheme(self):
        import configparser
        c = configparser.ConfigParser(inline_comment_prefixes=(";",))
        c.read(HERE / "tema/Bandanix/color.ini")
        scheme = c["Bandanix"]
        self.assertEqual(scheme["button"], "C8102E")
        for key, value in scheme.items():
            self.assertRegex(value, r"^[0-9A-F]{6}$", key)


if __name__ == "__main__":
    unittest.main()
