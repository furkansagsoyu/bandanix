"""When is something a problem? Limits, a one-minute CPU average and hysteresis."""
from __future__ import annotations

from collections import deque

DEFAULTS = {"islemci": 90, "sicaklik": 90, "ram": 90, "disk": 95}
RANGES = {"islemci": (50, 100), "sicaklik": (60, 105), "ram": (50, 99), "disk": (50, 99)}
CLEAR_GAP = 5               # a problem ends only this many points below its limit
CPU_WINDOW = 60             # seconds the CPU must stay high
TEMP_WINDOW = 30            # seconds the temperature is averaged over (turbo spikes are short)
PRIORITY = ("sicaklik", "ram", "islemci", "disk")
LABELS = {"sicaklik": "Sıcaklık", "ram": "RAM", "islemci": "İşlemci", "disk": "Disk"}


def limits_from(section: dict) -> dict[str, int]:
    out = dict(DEFAULTS)
    for key, (lo, hi) in RANGES.items():
        value = section.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and lo <= value <= hi:
            out[key] = value
    return out


def text_for(kind: str, value: float) -> str:
    if kind == "sicaklik":
        return f"{value:.0f}°C"
    return f"{LABELS[kind]} %{value:.0f}"


class Rules:
    def __init__(self, limits: dict[str, int] | None = None):
        self.limits = dict(limits or DEFAULTS)
        self.active: set[str] = set()
        self.cpu: deque = deque()          # (time, busy, total)
        self.temps: deque = deque()        # (time, °C)

    # ---- CPU average over the last minute ----------------------------------------------
    def _cpu(self, now: float, times: tuple[int, int] | None) -> tuple[float | None, float | None]:
        if times is None:
            return None, None
        instant = None
        if self.cpu:
            _, b0, t0 = self.cpu[-1]
            if times[1] > t0:
                instant = (times[0] - b0) / (times[1] - t0) * 100
        self.cpu.append((now, *times))
        # keep exactly one sample at or before the start of the window
        while len(self.cpu) > 1 and self.cpu[1][0] <= now - CPU_WINDOW:
            self.cpu.popleft()
        start = self.cpu[0]
        if now - start[0] < CPU_WINDOW - 1 or times[1] <= start[2]:
            return None, instant                          # not a full minute yet
        return (times[0] - start[1]) / (times[1] - start[2]) * 100, instant

    # ---- temperature averaged over the last half minute -----------------------------------
    def _temp(self, now: float, temp: float | None) -> float | None:
        if temp is None:
            self.temps.clear()
            return None
        self.temps.append((now, temp))
        while self.temps and self.temps[0][0] < now - TEMP_WINDOW:
            self.temps.popleft()
        if now - self.temps[0][0] < TEMP_WINDOW - 6:
            return None                                   # not half a minute of readings yet
        return sum(t for _, t in self.temps) / len(self.temps)

    # ---- one step ----------------------------------------------------------------------
    def update(self, now: float, cpu_times, temp, mem, disks) -> dict:
        cpu_avg, cpu_now = self._cpu(now, cpu_times)
        ram = mem[0] / mem[1] * 100 if mem and mem[1] else None
        disk = max((d.percent for d in disks), default=None)
        temp_avg = self._temp(now, temp)

        values = {"islemci": cpu_avg, "sicaklik": temp_avg, "ram": ram, "disk": disk}
        for kind, value in values.items():
            limit = self.limits[kind]
            if value is None:
                self.active.discard(kind)
            elif kind in self.active:
                if value < limit - CLEAR_GAP:
                    self.active.discard(kind)
            elif value > limit:
                self.active.add(kind)

        problems = [{"tur": k, "deger": round(values[k], 1), "yazi": text_for(k, values[k])}
                    for k in PRIORITY if k in self.active]
        return {
            "zaman": now,
            "olcum": {
                "islemci": None if cpu_avg is None else round(cpu_avg, 1),
                "islemci_anlik": None if cpu_now is None else round(cpu_now, 1),
                "sicaklik": temp,
                "sicaklik_ort": None if temp_avg is None else round(temp_avg, 1),
                "ram": None if ram is None else round(ram, 1),
                "ram_kullanilan": mem[0] if mem else None,
                "ram_toplam": mem[1] if mem else None,
                "diskler": [{"yol": d.path, "yuzde": d.percent, "bos": d.free} for d in disks],
            },
            "sinirlar": self.limits,
            "sorunlar": problems,
        }
