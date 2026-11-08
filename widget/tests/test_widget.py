"""Tests for the weather helper: python3 -m unittest discover widget/tests"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

TMP = Path(tempfile.mkdtemp())
os.environ["XDG_CONFIG_HOME"] = str(TMP / "config")
os.environ["XDG_CACHE_HOME"] = str(TMP / "cache")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bandanix_widget as w  # noqa: E402

SAMPLE = {
    "current": {"time": "2026-11-08T21:30", "temperature_2m": 6.4, "weather_code": 2, "is_day": 0},
    "daily": {
        "time": ["2026-11-08", "2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12"],
        "weather_code": [2, 3, 0, 63, 71],
        "temperature_2m_max": [8.1, 9.4, 11.0, 7.2, 3.0],
        "temperature_2m_min": [1.0, 2.2, 3.4, 4.0, -1.0],
    },
}


class Weather(unittest.TestCase):
    def test_build(self):
        data = w.build_weather(SAMPLE, "Ankara", 100.0)
        self.assertEqual(data["simdi"], {"sicaklik": 6, "yazi": "Parçalı bulutlu",
                                         "ikon": "weather-few-clouds-night-symbolic"})
        self.assertEqual([d["gun"] for d in data["gunler"]], ["Pazartesi", "Salı", "Çarşamba"])
        self.assertEqual((data["gunler"][2]["yazi"], data["gunler"][2]["en_yuksek"]), ("Yağmurlu", 7))

    def test_unknown_code(self):
        self.assertEqual(w.describe(1234)[0], "Bilinmiyor")
        self.assertEqual(w.describe(None)[0], "Bilinmiyor")


class Theme(unittest.TestCase):
    def setUp(self):
        w.THEME.parent.mkdir(parents=True, exist_ok=True)

    def test_new_section_and_update(self):
        w.THEME.write_text('[colors]\naccent = "#C8102E"\n\n[panel]\nduzen = "orta"\n')
        w.write_section({"sehir": "Ankara", "enlem": 39.92, "boylam": 32.85})
        self.assertEqual(w.read_section("[widget]"), {"sehir": "Ankara", "enlem": 39.92, "boylam": 32.85})
        w.write_section({"sehir": "Tokat", "enlem": 40.3139, "boylam": 36.5544})
        text = w.THEME.read_text()
        self.assertEqual(text.count("[widget]"), 1)
        self.assertIn('duzen = "orta"', text)
        self.assertEqual(w.read_section("[widget]")["sehir"], "Tokat")

    def test_section_in_the_middle_keeps_comments(self):
        w.THEME.write_text('[widget]\nsehir = ""        # yorum\n\n[panel]\nduzen = "orta"\n')
        w.write_section({"sehir": "İzmir", "enlem": 38.42, "boylam": 27.14})
        text = w.THEME.read_text()
        self.assertIn('sehir = "İzmir"        # yorum', text)
        self.assertLess(text.index("boylam"), text.index("[panel]"))


if __name__ == "__main__":
    unittest.main()
