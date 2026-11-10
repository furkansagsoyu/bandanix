"""Tests for power-mode detection: python3 -m unittest discover guc/tests"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(tempfile.mkdtemp())
os.environ["BANDANIX_GUC_KOK"] = str(ROOT)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bandanix_guc as g  # noqa: E402

EC = ROOT / "sys/devices/platform/msi-ec"
TURBO = ROOT / "sys/devices/system/cpu/intel_pstate/no_turbo"


def put(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class State(unittest.TestCase):
    def test_msi_modes(self):
        put(EC / "available_shift_modes", "turbo\neco\ncomfort\n")
        put(EC / "available_fan_modes", "auto\nsilent\nadvanced\n")
        put(EC / "fan_mode", "auto\n")
        put(EC / "cooler_boost", "off\n")
        for shift, no_turbo, want in (("comfort", "0", "dengeli"), ("comfort", "1", "serin"),
                                      ("eco", "0", "eco"), ("turbo", "0", "turbo")):
            put(EC / "shift_mode", shift + "\n")
            put(TURBO, no_turbo + "\n")
            s = g.state()
            self.assertEqual(s["mod"], want)
        self.assertEqual(s["modlar"], ["serin", "eco", "dengeli", "turbo"])
        self.assertEqual(s["fanlar"], ["auto", "silent"])        # "advanced" is not offered
        self.assertTrue(s["boost_var"])


if __name__ == "__main__":
    unittest.main()
