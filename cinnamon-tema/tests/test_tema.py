"""Theme builder on a tiny fake Mint-Y, and the lock screen settings helper."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


class TemaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)
        src = self.t / "Mint-Y-Dark-Red"
        (src / "gtk-3.0").mkdir(parents=True)
        (src / "gtk-3.0/gtk.css").write_text("button { color: #b92e3c; background: #383838; }\n"
                                              "button.suggested-action { background-color: #8fa876; }\n")
        (src / "index.theme").write_text("[Desktop Entry]\nName=Mint-Y-Dark-Red\nGtkTheme=Mint-Y-Dark-Red\n")
        self.src = src

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, accent):
        out = self.t / "Bandanix"
        subprocess.run(["/usr/bin/python3", str(HERE / "build_theme.py"), "--kaynak", str(self.src),
                        "--hedef", str(out), "--accent", accent], check=True, capture_output=True)
        return (out / "gtk-3.0/gtk.css").read_text()

    def test_buttons_and_lock_screen_follow_the_accent(self):
        css = self.build("#3366FF")
        tail = css[css.index("/* >>> bandanix >>>"):]
        self.assertIn("button.suggested-action", tail)
        self.assertIn("background-color: #3366FF;", tail)
        self.assertIn(".csstage .passwordentry", tail)
        self.assertIn("border-color: #3366FF;", tail[tail.index(".csstage"):])
        self.assertNotIn("#C8102E", tail)
        self.assertEqual(css.count("{"), css.count("}"))

    def test_lock_screen_settings(self):
        env = dict(os.environ, XDG_CONFIG_HOME=str(self.t / "conf"))
        run = lambda *a: subprocess.run(["/usr/bin/python3", str(HERE / "kilit_ekrani.py"), *a],
                                        env=env, capture_output=True, text=True)
        keys = run("anahtarlar").stdout.split()
        self.assertIn("dconf:/org/cinnamon/desktop/screensaver/floating-widgets", keys)
        self.assertEqual(len(keys), 9)
        import importlib.util
        spec = importlib.util.spec_from_file_location("kilit", HERE / "kilit_ekrani.py")
        kilit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(kilit)
        kilit.THEME = self.t / "theme.toml"
        self.assertEqual(kilit.values()["font-time"], "'Ubuntu Light 72'")
        kilit.THEME.write_text('[fonts]\nui = "Inter"\n')
        self.assertEqual(kilit.values()["font-date"], "'Inter 20'")
        kilit.THEME.write_text('[fonts]\nui = "x\' ; rm"\n')                 # never reaches dconf
        self.assertEqual(kilit.values()["font-time"], "'Ubuntu Light 72'")
        self.assertEqual(kilit.values()["floating-widgets"], "false")


if __name__ == "__main__":
    unittest.main()
