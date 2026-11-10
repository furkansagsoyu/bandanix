"""Tests for the system island's watcher (no Qt): python3 -m unittest discover sistem-adasi/tests

Run from the repo root with PYTHONPATH=sistem-adasi:ortak/ada
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(tempfile.mkdtemp())
os.environ["BANDANIX_SISTEM_KOK"] = str(ROOT)
sys.path[:0] = [str(Path(__file__).resolve().parents[1]),
                str(Path(__file__).resolve().parents[2] / "ortak" / "ada")]

from bandanix_ada import dizilim  # noqa: E402
from bandanix_sistem import olcum  # noqa: E402
from bandanix_sistem.kurallar import Rules, limits_from  # noqa: E402


def write(rel, text):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class Readers(unittest.TestCase):
    def test_cpu_and_memory(self):
        write("proc/stat", "cpu  100 0 50 800 50 0 0 0 0 0\ncpu0 1 2 3 4\ncpu1 1 2 3 4\n")
        self.assertEqual(olcum.cpu_times(), (150, 1000))
        self.assertEqual(olcum.cpu_count(), 2)
        write("proc/meminfo", "MemTotal:       16000000 kB\nMemFree: 1 kB\nMemAvailable:    4000000 kB\n")
        self.assertEqual(olcum.memory(), (12000000 * 1024, 16000000 * 1024))

    def test_temperature_prefers_cpu_package(self):
        write("sys/class/hwmon/hwmon0/name", "nvme\n")
        write("sys/class/hwmon/hwmon0/temp1_input", "99000\n")
        write("sys/class/hwmon/hwmon1/name", "coretemp\n")
        write("sys/class/hwmon/hwmon1/temp1_input", "71000\n")
        write("sys/class/hwmon/hwmon1/temp2_input", "68500\n")
        self.assertEqual(olcum.temperature(), 71.0)

    def test_human(self):
        self.assertEqual(olcum.human(512 * 1024 * 1024), "512 MB")
        self.assertEqual(olcum.human(3.5 * 1024 ** 3), "3.5 GB")


class Disk:
    def __init__(self, percent):
        self.percent, self.path, self.free = percent, "/", 1


class RulesTest(unittest.TestCase):
    def test_cpu_needs_a_full_minute(self):
        r = Rules()
        busy, total = 0, 0
        for second in range(0, 70, 5):
            state = r.update(second, (busy, total), 50, (1, 10), [])
            busy, total = busy + 97, total + 100
            if second < 60:
                self.assertEqual(state["sorunlar"], [], second)
        self.assertEqual([p["tur"] for p in state["sorunlar"]], ["islemci"])
        self.assertEqual(state["sorunlar"][0]["yazi"], "İşlemci %97")

    def test_hysteresis_and_priority(self):
        r = Rules()
        s = r.update(0, None, 50, (95, 100), [Disk(96)])
        self.assertEqual([p["tur"] for p in s["sorunlar"]], ["ram", "disk"])
        s = r.update(5, None, 50, (88, 100), [Disk(92)])            # inside the 5 point gap
        self.assertEqual([p["tur"] for p in s["sorunlar"]], ["ram", "disk"])
        s = r.update(10, None, 50, (84, 100), [Disk(89)])
        self.assertEqual(s["sorunlar"], [])

    def test_temperature_is_averaged_over_half_a_minute(self):
        r = Rules()
        # a short turbo spike: 95 for 10 s between cool readings -> no warning
        for second, temp in enumerate([50, 50, 95, 95, 50, 50, 50, 50]):
            self.assertEqual(r.update(second * 5, None, temp, None, [])["sorunlar"], [], second)
        # really hot for half a minute -> warning with the average
        r = Rules()
        state = {}
        for second in range(0, 35, 5):
            state = r.update(second, None, 96, None, [])
        self.assertEqual(state["sorunlar"][0]["yazi"], "96°C")
        self.assertEqual(state["olcum"]["sicaklik_ort"], 96.0)

    def test_limits_from_theme(self):
        self.assertEqual(limits_from({"ram": 80, "disk": 200, "sicaklik": True})["ram"], 80)
        self.assertEqual(limits_from({"disk": 200})["disk"], 95)
        self.assertEqual(limits_from({"sicaklik": True})["sicaklik"], 90)


class Layout(unittest.TestCase):
    def test_place_beside(self):
        self.assertEqual(dizilim.place_beside({"x": 800, "y": 8, "w": 320, "h": 42}, 120, 0, 1920, 8),
                         (1128, 8))
        self.assertEqual(dizilim.place_beside(None, 120, 0, 1920, 8), (900, 8))
        self.assertEqual(dizilim.place_beside({"x": 1700, "y": 8, "w": 200, "h": 42}, 360, 0, 1920, 8),
                         (1552, 8))

    def test_registry_ignores_dead_or_hidden(self):
        os.environ["XDG_RUNTIME_DIR"] = tempfile.mkdtemp()
        dizilim.publish("a", 1, 2, 3, 4, True)
        self.assertEqual(dizilim.read("a")["w"], 3)
        dizilim.publish("a", 1, 2, 3, 4, False)
        self.assertIsNone(dizilim.read("a"))
        dizilim.remove("a")
        self.assertIsNone(dizilim.read("a"))


if __name__ == "__main__":
    unittest.main()
