import tempfile
import unittest
from pathlib import Path

from sound_island.config import BANDANA_RED, Theme, load_theme


class ThemeTests(unittest.TestCase):
    def write(self, text: str) -> Path:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False, encoding="utf-8")
        tmp.write(text)
        tmp.close()
        self.addCleanup(Path(tmp.name).unlink)
        return Path(tmp.name)

    def test_missing_file_gives_defaults(self):
        self.assertEqual(load_theme(Path("/nonexistent/theme.toml")), Theme())
        self.assertEqual(Theme().accent, BANDANA_RED)

    def test_reads_values(self):
        theme = load_theme(self.write(
            '[colors]\naccent = "#1DB954"\n[fonts]\nui = " Inter "\n'
            '[sound-island]\nfollow_cover = false\nhide_when_idle = false\n'
            'bars = "simulated"\ngosterge = false\n'))
        self.assertEqual(theme, Theme(accent="#1DB954", font="Inter",
                                      follow_cover=False,
                                      bars="simulated", gosterge=False))

    def test_bad_values_fall_back(self):
        theme = load_theme(self.write(
            '[colors]\naccent = "red"\n[sound-island]\nfollow_cover = "yes"\n'
            'bars = "laser"\n'))
        self.assertEqual(theme.accent, BANDANA_RED)
        self.assertTrue(theme.follow_cover)
        self.assertEqual(theme.bars, "auto")

    def test_broken_toml_gives_defaults(self):
        self.assertEqual(load_theme(self.write("this is [ not toml")), Theme())


if __name__ == "__main__":
    unittest.main()
