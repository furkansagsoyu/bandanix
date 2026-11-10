#!/usr/bin/env python3
"""bandanix-pil: battery health helper for the Bandanix kit.

  bandanix-pil              same as "durum"
  bandanix-pil durum        charge, health, cycle count and the charge limit
  bandanix-pil tam          charge to 100% once (e.g. before a trip); the limit comes back
                            by itself when the battery is full or the charger is unplugged
  bandanix-pil sinir 85     change the kept charge limit (50-100, saved in theme.toml)
  bandanix-pil kontrol      run by the user timer every 2 minutes: low battery warning etc.

Only the tiny root helper (/usr/local/sbin/bandanix-pil-yaz) writes the hardware limit;
this program calls it through "sudo -n" and never asks for a password itself.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
import bandanix_tema  # noqa: E402  (shared theme.toml writer)

HOME = Path.home()
SYSFS = Path(os.environ.get("BANDANIX_PIL_SYSFS", "/sys/class/power_supply"))
CONF = Path(os.environ.get("BANDANIX_PIL_CONF", "/etc/bandanix-pil.conf"))
HELPER = "/usr/local/sbin/bandanix-pil-yaz"
WRITER = shlex.split(os.environ.get("BANDANIX_PIL_YAZ", f"sudo -n {HELPER}"))
THEME = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config") / "bandanix" / "theme.toml"
STATE = Path(os.environ.get("XDG_STATE_HOME") or HOME / ".local" / "state") / "bandanix" / "pil.json"

DEFAULTS = {"ust": 80, "alt": 20}

USAGE = """Kullanım:
  bandanix-pil              pilin durumu (şarj, sağlık, döngü, sınır)
  bandanix-pil tam          bu seferlik %100'e kadar şarj et (yolculuk öncesi gibi);
                            dolunca ya da şarj aletini çıkarınca sınır kendiliğinden geri gelir
  bandanix-pil sinir 85     şarj sınırını değiştir (50-100)"""
RANGES = {"ust": (50, 100), "alt": (5, 50)}


def say(msg: str) -> None:
    print(f"• {msg}")


# ---- sysfs ----------------------------------------------------------------------------
def battery() -> Path | None:
    for p in sorted(SYSFS.glob("BAT*")):
        if (p / "capacity").is_file():
            return p
    return None


def charger_online() -> bool | None:
    found = None
    for p in sorted(SYSFS.iterdir()) if SYSFS.is_dir() else []:
        if read(p / "type") == "Mains":
            found = found or read(p / "online") == "1"
    return found


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def read_int(path: Path) -> int | None:
    value = read(path)
    return int(value) if re.fullmatch(r"-?\d+", value) else None


def hw_limit(bat: Path | None) -> int | None:
    return read_int(bat / "charge_control_end_threshold") if bat else None


def kept_limit() -> int | None:
    m = re.search(r"^SINIR=(\d{2,3})$", read(CONF), re.M)
    return int(m.group(1)) if m else None


# ---- theme.toml [pil] (read and minimal in-place edit, keeping the user's other lines) --
SECTION = "[pil]"


def setting(key: str) -> int:
    section = ""
    lo, hi = RANGES[key]
    for line in read(THEME).splitlines():
        if line.strip().startswith("["):
            section = line.strip()
        elif section == SECTION:
            m = re.match(rf"^\s*{key}\s*=\s*(\d+)", line)
            if m and lo <= int(m.group(1)) <= hi:
                return int(m.group(1))
    return DEFAULTS[key]


def write_setting(key: str, value: int) -> None:
    bandanix_tema.set_values("pil", {key: value}, THEME)


# ---- state ----------------------------------------------------------------------------
def load_state() -> dict:
    try:
        data = json.loads(STATE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state), encoding="utf-8")


# ---- actions --------------------------------------------------------------------------
def write_limit(*args: str) -> bool:
    try:
        r = subprocess.run([*WRITER, *args], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return False
    if r.returncode != 0 and r.stderr.strip():
        print(r.stderr.strip(), file=sys.stderr)
    return r.returncode == 0


def notify(title: str, body: str, icon: str, urgent: bool = False) -> None:
    env = dict(os.environ)
    env.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path=/run/user/{os.getuid()}/bus")
    cmd = ["notify-send", "-a", "Bandanix", "-i", icon]
    if urgent:
        cmd += ["-u", "critical"]
    try:
        subprocess.run([*cmd, title, body], env=env, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        pass


STATUS_TR = {
    "Charging": "şarj oluyor",
    "Discharging": "pilden çalışıyor",
    "Full": "dolu",
    "Not charging": "şarj aletinde, şarj etmiyor (sınırda)",
}


def energy(bat: Path) -> tuple[float | None, float | None, str]:
    """Full and design capacity in Wh (or mAh when the battery reports charge)."""
    for prefix, unit in (("energy", "Wh"), ("charge", "mAh")):
        full = read_int(bat / f"{prefix}_full")
        design = read_int(bat / f"{prefix}_full_design")
        if full and design:
            scale = 1e6 if unit == "Wh" else 1e3
            return full / scale, design / scale, unit
    return None, None, ""


def remaining(bat: Path, status: str) -> str:
    now = read_int(bat / "energy_now") or read_int(bat / "charge_now")
    rate = read_int(bat / "power_now") or read_int(bat / "current_now")
    if not now or not rate or rate <= 0 or status != "Discharging":
        return ""
    hours = now / rate
    return f"{int(hours)} sa {int(hours % 1 * 60):02d} dk"


def durum() -> int:
    bat = battery()
    if not bat:
        say("Pil bulunamadı (masaüstü bilgisayar mı?).")
        return 1
    cap = read_int(bat / "capacity")
    status = read(bat / "status")
    print(f"Pil         %{cap}  ({STATUS_TR.get(status, status.lower() or 'bilinmiyor')})")
    left = remaining(bat, status)
    if left:
        print(f"Kalan       yaklaşık {left}")
    full, design, unit = energy(bat)
    if full and design:
        fmt = "{:.1f}" if unit == "Wh" else "{:.0f}"
        print(f"Sağlık      %{round(full / design * 100)}  "
              f"(şimdi {fmt.format(full)} {unit}, ilk hâli {fmt.format(design)} {unit})")
    cycles = read_int(bat / "cycle_count")
    if cycles:
        print(f"Döngü       {cycles}")
    limit = hw_limit(bat)
    if limit is None:
        print(f"Sınır       donanım desteklemiyor; %{setting('ust')} olunca bildirim gelir")
    else:
        kept = kept_limit()
        line = f"Sınır       %{limit}"
        if load_state().get("tam"):
            line += f"  (tek seferlik tam şarj; sonra %{kept or setting('ust')})"
        elif kept and kept != limit:
            line += f"  (kayıtlı: %{kept})"
        print(line)
    print(f"Uyarı       %{setting('alt')} altına inince")
    return 0


def tam() -> int:
    bat = battery()
    if not bat or hw_limit(bat) is None:
        say("Bu bilgisayarda şarj sınırı yok, zaten %100'e kadar şarj oluyor.")
        return 0
    if charger_online() is False:
        say("Şarj aleti takılı değil. Tak, sonra tekrar çalıştır.")
        return 1
    if not write_limit("100"):
        say("Sınır değiştirilemedi. Pil parçasını yeniden kur: ./install.sh pil")
        return 1
    state = load_state()
    state["tam"] = True
    save_state(state)
    say("Bu seferlik %100'e kadar şarj olacak.")
    say(f"Dolunca ya da şarj aletini çıkarınca sınır kendiliğinden %{kept_limit() or setting('ust')} olur.")
    return 0


def sinir(arg: str) -> int:
    lo, hi = RANGES["ust"]
    if not re.fullmatch(r"\d{2,3}", arg) or not lo <= int(arg) <= hi:
        say(f"Sınır {lo} ile {hi} arasında bir sayı olmalı (ör. bandanix-pil sinir 80).")
        return 2
    value = int(arg)
    bat = battery()
    if bat and hw_limit(bat) is not None:
        if not write_limit("--kalici", str(value)):
            say("Sınır değiştirilemedi. Pil parçasını yeniden kur: ./install.sh pil")
            return 1
        state = load_state()
        state.pop("tam", None)
        save_state(state)
        say(f"Şarj sınırı %{value}. Her açılışta ve uykudan uyanınca uygulanır.")
    else:
        say(f"Donanım sınırı yok; şarj %{value} olunca bildirim gelecek.")
    write_setting("ust", value)
    return 0


def kontrol() -> int:
    bat = battery()
    if not bat:
        return 0
    cap = read_int(bat / "capacity")
    if cap is None:
        return 0
    status = read(bat / "status")
    plugged = charger_online()
    if plugged is None:
        plugged = status != "Discharging"
    state = load_state()
    before = dict(state)
    limit = hw_limit(bat)
    alt, ust = setting("alt"), setting("ust")

    # one-time full charge: put the kept limit back when full or unplugged
    if state.get("tam"):
        if limit != 100:                     # a reboot already restored it
            state.pop("tam")
        elif (not plugged or cap >= 100 or status == "Full"
              or (status == "Not charging" and cap >= 95)):
            if write_limit("--kayitli"):
                state.pop("tam")
                back = kept_limit() or ust
                notify("Tam şarj bitti", f"Şarj sınırı tekrar %{back}.", "battery-full-charged")

    # low battery: once each time it drops below the line
    if not plugged and cap <= alt:
        if not state.get("dusuk"):
            notify(f"Pil %{cap}", "Şarj aletini tak.", "battery-caution", urgent=True)
            state["dusuk"] = True
    elif plugged or cap > alt:
        state.pop("dusuk", None)

    # no hardware limit: tell the user when it reaches the line while charging
    if limit is None and ust < 100:
        if plugged and cap >= ust:
            if not state.get("ust"):
                notify(f"Pil %{cap}", "Pilin ömrü için şarj aletini çıkarabilirsin.", "battery-good")
                state["ust"] = True
        elif not plugged:
            state.pop("ust", None)

    if state != before:
        save_state(state)
    return 0


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "durum"
    if cmd == "durum" and len(argv) <= 1:
        return durum()
    if cmd == "tam" and len(argv) == 1:
        return tam()
    if cmd == "sinir" and len(argv) == 2:
        return sinir(argv[1])
    if cmd == "kontrol" and len(argv) == 1:
        return kontrol()
    if cmd in ("ust", "alt") and len(argv) == 1:  # used by install.sh
        print(setting(cmd))
        return 0
    helped = cmd in ("-h", "--help", "yardim")
    print(USAGE, file=sys.stdout if helped else sys.stderr)
    return 0 if helped else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
