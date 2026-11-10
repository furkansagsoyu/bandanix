#!/usr/bin/env python3
"""bandanix-guc: power modes, fan mode and Cooler Boost.

  bandanix-guc                       current mode, fans, turbo and temperature
  bandanix-guc serin|eco|dengeli|turbo
  bandanix-guc fan otomatik|sessiz
  bandanix-guc boost [kapat]         fans at full speed for 5 minutes

Only the small root helper (/usr/local/sbin/bandanix-guc-yaz) writes anything; this program
calls it through "sudo -n" and never asks for a password itself.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("BANDANIX_GUC_KOK", "/"))            # tests point this elsewhere
EC = ROOT / "sys/devices/platform/msi-ec"
NO_TURBO = ROOT / "sys/devices/system/cpu/intel_pstate/no_turbo"
BOOST = ROOT / "sys/devices/system/cpu/cpufreq/boost"
HWMON = ROOT / "sys/class/hwmon"
HELPER = "/usr/local/sbin/bandanix-guc-yaz"
WRITER = shlex.split(os.environ.get("BANDANIX_GUC_YAZ", f"sudo -n {HELPER}"))

MODES = {
    "serin": ("Serin", "turbo kapalı; dizi, ders, yazı"),
    "eco": ("Eco", "pilde uzun kullanım"),
    "dengeli": ("Dengeli", "günlük kullanım"),
    "turbo": ("Turbo", "oyun, derleme"),
}
FANS = {"otomatik": "auto", "sessiz": "silent"}
FAN_NAMES = {"auto": "otomatik", "silent": "sessiz", "advanced": "gelişmiş", "basic": "temel"}

USAGE = """Kullanım:
  bandanix-guc                         şu anki mod, fanlar, turbo ve sıcaklık
  bandanix-guc serin|eco|dengeli|turbo modu değiştir
  bandanix-guc fan otomatik|sessiz     fan modunu değiştir
  bandanix-guc boost                   fanlar 5 dakika tam hız (erken kapatmak için: boost kapat)"""


def say(msg: str) -> None:
    print(f"• {msg}")


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def turbo_on() -> bool | None:
    if NO_TURBO.is_file():
        return read(NO_TURBO) == "0"
    if BOOST.is_file():
        return read(BOOST) == "1"
    return None


def temperature() -> float | None:
    best: dict[str, float] = {}
    for hw in sorted(HWMON.glob("hwmon*")) if HWMON.is_dir() else []:
        name = read(hw / "name")
        if name not in ("coretemp", "k10temp", "zenpower", "acpitz"):
            continue
        for inp in hw.glob("temp*_input"):
            raw = read(inp)
            if raw.isdigit() and 0 < int(raw) / 1000 < 150:
                best[name] = max(best.get(name, 0.0), int(raw) / 1000)
    for name in ("coretemp", "k10temp", "zenpower", "acpitz"):
        if name in best:
            return best[name]
    return None


def state() -> dict:
    shift, turbo = read(EC / "shift_mode"), turbo_on()
    if turbo is False and shift in ("comfort", ""):
        mode = "serin"
    elif shift == "eco":
        mode = "eco"
    elif shift == "turbo":
        mode = "turbo"
    elif shift == "comfort" or (not shift and turbo):
        mode = "dengeli"
    else:
        mode = ""
    shifts = read(EC / "available_shift_modes").split()
    modes = [m for m in MODES
             if (m == "serin" and turbo is not None) or (m == "dengeli")
             or (m in ("eco", "turbo") and m in shifts)]
    fans = [f for f in read(EC / "available_fan_modes").split() if f in FANS.values()]
    return {
        "msi": EC.is_dir(), "mod": mode, "modlar": modes, "guc_modu": shift,
        "turbo": turbo, "fan": read(EC / "fan_mode"), "fanlar": fans,
        "boost": read(EC / "cooler_boost") == "on", "boost_var": (EC / "cooler_boost").is_file(),
        "sicaklik": temperature(),
    }


def write(*args: str) -> bool:
    try:
        r = subprocess.run([*WRITER, *args], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return False
    if r.returncode != 0 and r.stderr.strip():
        print(r.stderr.strip(), file=sys.stderr)
    return r.returncode == 0


FAILED = "Değiştirilemedi. Parçayı yeniden kur: ./install.sh guc"


def cmd_show() -> int:
    s = state()
    name = MODES[s["mod"]][0] if s["mod"] in MODES else "özel"
    print(f"Mod         {name}" + (f"  ({MODES[s['mod']][1]})" if s["mod"] in MODES else ""))
    if s["turbo"] is not None:
        print(f"Turbo       {'açık' if s['turbo'] else 'kapalı'}")
    if s["msi"]:
        print(f"Fanlar      {FAN_NAMES.get(s['fan'], s['fan'] or '-')}" + ("  + Cooler Boost" if s["boost"] else ""))
    else:
        print("Fanlar      bu bilgisayarda MSI fan kontrolü yok")
    if s["sicaklik"] is not None:
        print(f"Sıcaklık    {s['sicaklik']:.0f}°C")
    print()
    print("Modlar: " + ", ".join(s["modlar"]))
    return 0


def cmd_mode(mode: str) -> int:
    if mode not in state()["modlar"]:
        say(f"Bu bilgisayar \"{mode}\" modunu desteklemiyor.")
        return 1
    if not write("mod", mode):
        say(FAILED)
        return 1
    say(f"Mod: {MODES[mode][0]} ({MODES[mode][1]}). Her açılışta uygulanır.")
    return 0


def cmd_fan(name: str) -> int:
    if name not in FANS:
        print(USAGE, file=sys.stderr)
        return 2
    if FANS[name] not in state()["fanlar"]:
        say("Bu bilgisayar bu fan modunu desteklemiyor.")
        return 1
    if not write("fan", FANS[name]):
        say(FAILED)
        return 1
    say(f"Fan modu: {name}.")
    return 0


def cmd_boost(on: bool) -> int:
    if not state()["boost_var"]:
        say("Bu bilgisayarda Cooler Boost yok.")
        return 1
    if not write("boost", "on" if on else "off"):
        say(FAILED)
        return 1
    say("Cooler Boost açık; 5 dakika sonra kendiliğinden kapanır." if on else "Cooler Boost kapalı.")
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        return cmd_show()
    cmd = argv[0]
    if cmd in MODES and len(argv) == 1:
        return cmd_mode(cmd)
    if cmd == "fan" and len(argv) == 2:
        return cmd_fan(argv[1])
    if cmd == "boost" and len(argv) == 1:
        return cmd_boost(True)
    if cmd == "boost" and argv[1:] == ["kapat"]:
        return cmd_boost(False)
    if cmd == "_json" and len(argv) == 1:
        print(json.dumps(state(), ensure_ascii=False))
        return 0
    helped = cmd in ("-h", "--help", "yardim")
    print(USAGE, file=sys.stdout if helped else sys.stderr)
    return 0 if helped else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
